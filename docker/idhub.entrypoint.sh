#!/bin/sh

set -e
set -u
set -x


usage() {
                cat <<END
ERROR: you need to map your idhub git repo volume to docker, suggested volume mapping is:

    volumes:
      - ./IdHub:/opt/idhub
END
                exit 1
}

detect_app_version() {
        if [ -d "${APP_DIR}/.git" ]; then
                git_commit_info="$(gosu ${APP} git log --pretty=format:'%h' -n 1)"
                export COMMIT="version: commit ${git_commit_info}"
        else
                # TODO if software is packaged in setup.py and/or pyproject.toml we can get from there the version
                #   then we might want to distinguish prod version (stable version) vs development (commit/branch)
                export COMMIT="version: unknown (reason: git undetected)"
        fi
}

gen_env_vars() {
        INIT_ORG="${INIT_ORG:-example-org}"
        INIT_ADMIN_USER="${INIT_ADMIN_EMAIL:-user@example.org}"
        INIT_ADMIN_PASSWD="${INIT_ADMIN_PASSWORD:-1234}"

        detect_app_version

        gosu ${APP} tee status_data <<END
DOMAIN=${DOMAIN}
END
}

init_db() {
        echo "INFO: INIT IDHUB DATABASE"
        # this file helps all docker containers to guess number of hosts involved
        #   right now is only needed by new deployment for oidc
        if [ -d "/sharedsecret" ]; then
                touch /sharedsecret/${DOMAIN}
        fi

        # move the migrate thing in docker entrypoint
        #   inspired by https://medium.com/analytics-vidhya/django-with-docker-and-docker-compose-python-part-2-8415976470cc
        gosu ${APP} ./manage.py migrate

        # init data
        if [ "${DEMO:-}" = 'true' ]; then
                printf "This is DEVELOPMENT/PILOTS_EARLY DEPLOYMENT: including demo hardcoded data\n" >&2
                PREDEFINED_TOKEN="${PREDEFINED_TOKEN:-}"
                gosu ${APP} ./manage.py demo_data "${PREDEFINED_TOKEN}"
        else
                gosu ${APP} ./manage.py init_org "${INIT_ORG}"
                gosu ${APP} ./manage.py init_admin "${INIT_ADMIN_EMAIL}" "${INIT_ADMIN_PASSWORD}"
        fi

        if [ -f "${OIDC_ORGS:-}" ]; then
                config_oidc4vp
        else
                echo "Note: skipping oidc4vp config"
        fi

}

manage_db() {
        if [ "${DB_TYPE:-}" = "postgres" ]; then
                echo "INFO: WAITING DATABASE CONNECTIVITY"
                # TODO hardcoded only for this docker compose deployment
                DB_HOST=idhub-postgres
                #   https://github.com/docker-library/postgres/issues/146#issuecomment-213545864
                #   https://github.com/docker-library/postgres/issues/146#issuecomment-2905869196
                while ! pg_isready -h "${DB_HOST}"; do
                        sleep 1
                done
        fi
        if [ "${REMOVE_DATA}" = "true" ]; then
                echo "INFO: REMOVE IDHUB DATABASE (reason: IDHUB_REMOVE_DATA is equal to true)"
                # https://django-extensions.readthedocs.io/en/latest/reset_db.html
                # https://github.com/django-cms/django-cms/issues/5921#issuecomment-343658455
                gosu ${APP} ./manage.py reset_db --close-sessions --noinput
                init_db
        else
                echo "INFO: PRESERVE IDHUB DATABASE"
                gosu ${APP} ./manage.py migrate
                # warn admin that it should re-enter password to keep the service working
                gosu ${APP} ./manage.py send_mail_admins
        fi
}

_set() {
        key="${1}"
        value="${2}"
        domain="${3}"
        sqlite3 db.sqlite3 "update oidc4vp_organization set ${key}='${value}' where domain='${domain}';"
}

_get() {
        sqlite3 -json db.sqlite3 "select * from oidc4vp_organization;"
}

_lines () {
        local myfile="${1}"
        cat "${myfile}" | wc -l
}

config_oidc4vp() {
        # populate your config
        data="$(_get)"
        echo "${data}" | jq --arg domain "${DOMAIN}" '{ ($domain): .}' > /sharedsecret/${DOMAIN}

        while true; do
                echo wait the other idhubs to write, this is the only oportunity to sync with other idhubs in the docker compose
                ## break when no empty files left
                if ! wc -l /sharedsecret/* | awk '{print $1;}' | grep -qE '^0$'; then
                        break
                fi
                sleep 1
        done
        # get other configs
        for host in /sharedsecret/*; do
                # we are flexible on querying for DOMAIN: the first one based on regex
                target_domain="$(cat "${host}" | jq -r 'keys[0]')"
                if [ "${target_domain}" != "${DOMAIN}" ]; then
                        filtered_data="$(cat "${host}" | jq --arg domain "${DOMAIN}" 'first(.[][] | select(.domain | test ($domain)))')"
                        client_id="$(echo "${filtered_data}" | jq -r '.client_id')"
                        client_secret="$(echo "${filtered_data}" | jq -r '.client_secret')"

                        _set my_client_id ${client_id} ${target_domain}
                        _set my_client_secret ${client_secret} ${target_domain}
                fi
        done
}

runserver() {
        PORT="${PORT:-8000}"

        if [ "${DEBUG:-}" = 'true' ]; then
                gosu ${APP} ./manage.py print_settings
        fi

        if [ ! "${DEBUG:-}" = "true" ]; then
                gosu ${APP} ./manage.py collectstatic
                if [ "${EXPERIMENTAL:-}" = "true" ]; then
                        # reloading on source code changing is a debugging future, maybe better then use debug
                        #   src https://stackoverflow.com/questions/12773763/gunicorn-autoreload-on-source-change/24893069#24893069
                        # gunicorn with 1 worker, with more than 1 worker this is not expected to work
                        gunicorn --access-logfile - --error-logfile - -b :${PORT} trustchain_idhub.wsgi:application
                else
                        gosu ${APP} ./manage.py runserver 0.0.0.0:${PORT}
                fi
        elif [ "${DEMO_AUTODECRYPT:-}" = 'true' ]; then
                DEMO_VAULT_PASSWORD="DEMO"
                # open_service: automatically unlocks the vault,
                #   and runs the service
                #   useful for debugging/dev/demo purposes ./manage.py
                gosu ${APP} ./manage.py open_service "${DEMO_VAULT_PASSWORD}" 0.0.0.0:${PORT}
        else
                gosu ${APP} ./manage.py runserver 0.0.0.0:${PORT}
        fi
}

check_app_is_there() {
        if [ ! -f "./manage.py" ]; then
                usage
        fi
}

_prepare() {
        APP=idhub
        # src https://denibertovic.com/posts/handling-permissions-with-docker-volumes/
        #   via https://github.com/moby/moby/issues/22258#issuecomment-293664282
        #   related https://github.com/moby/moby/issues/2259
        USER_ID=${LOCAL_USER_ID:-9001}
        if ! id -u "${APP}" >/dev/null 2>&1; then
                useradd --shell /bin/bash -u $USER_ID -o -c "" -m ${APP}
        fi
        APP_DIR="/opt/${APP}"
        cd "${APP_DIR}"
}

main() {

        _prepare

        check_app_is_there

        gen_env_vars

        manage_db

        runserver
}

main "${@}"
