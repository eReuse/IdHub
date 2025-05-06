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
                git_commit_info="$(gosu ${APP_USER} git log --pretty=format:'%h' -n 1)"
                export COMMIT="version: commit ${git_commit_info}"
        else
                # TODO if software is packaged in setup.py and/or pyproject.toml we can get from there the version
                #   then we might want to distinguish prod version (stable version) vs development (commit/branch)
                export COMMIT="version: unknown (reason: git undetected)"
        fi
}

wait_dpp_services() {
        OPERATOR_TOKEN_FILE='operator-token.txt'
        ADMIN_TOKEN_FILE=api-connector_admin-token.txt
        VERAMO_API_CRED_FILE=pyvckit-api_credential.json
        while true; do
                # specially ensure VERAMO_API_CRED_FILE is not empty,
                #   it takes some time to get data in
                if [ -f "/shared/${ADMIN_TOKEN_FILE}" ] && \
                    [ -f "/shared/${VERAMO_API_CRED_FILE}" ] && \
                    ! wc -l "/shared/${VERAMO_API_CRED_FILE}" | awk '{print $1;}' | grep -qE '^0$'; then
                        sleep 5
                        echo "Files ready to process."
                        break
                else
                        echo "Waiting for files in shared: (1) ${ADMIN_TOKEN_FILE}, (2) ${VERAMO_API_CRED_FILE}"
                        sleep 5
                fi
        done
}

gen_env_vars() {
        INIT_ORGANIZATION="${INIT_ORG:-example-org}"
        INIT_ADMIN_USER="${INIT_ADMIN_EMAIL:-user@example.org}"
        INIT_ADMIN_PASSWD="${INIT_ADMIN_PASSWORD:-1234}"

        detect_app_version

        gosu ${APP_USER} tee status_data <<END
DOMAIN=${DOMAIN}
END


        if [ "${DEBUG:-}" = 'true' ]; then
                gosu ${APP_USER} ./manage.py print_settings
        fi

        if [ "${DPP:-}" = 'true' ]; then
                wait_dpp_services
                export API_DLT_OPERATOR_TOKEN="$(cat "/shared/${OPERATOR_TOKEN_FILE}")"
        fi
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
        gosu ${APP_USER} ./manage.py migrate

        # init data
        if [ "${DEMO:-}" = 'true' ]; then
                printf "This is DEVELOPMENT/PILOTS_EARLY DEPLOYMENT: including demo hardcoded data\n" >&2
                DEMO_CREATE_SCHEMAS="${DEMO_CREATE_SCHEMAS:-true}"
                DEMO_PREDEFINED_TOKEN="${DEMO_PREDEFINED_TOKEN:-}"
                gosu ${APP_USER} ./manage.py demo_data "${DEMO_PREDEFINED_TOKEN}"
                if [ "${DPP:-}" = 'true' ]; then
                        # because of verification, we need to wait that the server is up
                        ( sleep 20 && gosu ${APP_USER} ./manage.py demo_data_dpp ) &
                fi
        else
                gosu ${APP_USER} ./manage.py init_org "${INIT_ORGANIZATION}"
                gosu ${APP_USER} ./manage.py init_admin "${INIT_ADMIN_EMAIL}" "${INIT_ADMIN_PASSWORD}"
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
                gosu ${APP_USER} ./manage.py reset_db --close-sessions --noinput
        else
                echo "INFO: PRESERVE IDHUB DATABASE"
        fi

        # detect if is an existing deployment
        if gosu ${APP_USER} ./manage.py showmigrations --plan \
                        | grep -F -q '[X]  idhub_auth.0001_initial'; then
                echo "INFO: detected EXISTING deployment"
                gosu ${APP_USER} ./manage.py migrate
                # warn admin that it should re-enter password to keep the service working
                gosu ${APP_USER} ./manage.py send_mail_admins
        else
                echo "INFO detected NEW deployment"
                init_db
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

        gosu ${APP_USER} ./manage.py check --deploy

        if [ "${DEBUG:-}" = "false" ]; then
                gosu ${APP_USER} ./manage.py collectstatic
                if [ "${EXPERIMENTAL:-}" = "true" ]; then
                        # reloading on source code changing is a debugging future, maybe better then use debug
                        #   src https://stackoverflow.com/questions/12773763/gunicorn-autoreload-on-source-change/24893069#24893069
                        # gunicorn with 1 worker, with more than 1 worker this is not expected to work
                        gunicorn --access-logfile - --error-logfile - -b :${PORT} trustchain_idhub.wsgi:application
                else
                        gosu ${APP_USER} ./manage.py runserver 0.0.0.0:${PORT}
                fi
        elif [ "${DEMO_AUTODECRYPT:-}" = 'true' ]; then
                DEMO_VAULT_PASSWORD="DEMO"
                # open_service: automatically unlocks the vault,
                #   and runs the service
                #   useful for debugging/dev/demo purposes ./manage.py
                gosu ${APP_USER} ./manage.py open_service "${DEMO_VAULT_PASSWORD}" 0.0.0.0:${PORT}
        else
                gosu ${APP_USER} ./manage.py runserver 0.0.0.0:${PORT}
        fi
}

check_app_is_there() {
        if [ ! -f "./manage.py" ]; then
                usage
        fi
}

_detect_proper_user() {
        # src https://denibertovic.com/posts/handling-permissions-with-docker-volumes/
        #   via https://github.com/moby/moby/issues/22258#issuecomment-293664282
        #   related https://github.com/moby/moby/issues/2259

        # user of current dir
        USER_ID="$(stat -c "%u" .)"
        if [ "${USER_ID}" = "0" ]; then
                APP_USER="root"
        else
                APP_USER="${APP}"
                if ! id -u "${APP_USER}" >/dev/null 2>&1; then
                        useradd --shell /bin/bash -u ${USER_ID} -o -c "" -m ${APP_USER}
                fi
        fi
}

_prepare() {
        APP=idhub
        _detect_proper_user
        # docker create root owned volumes, it is our job to map it to
        #   the right user
        chown -R ${APP_USER}: "${MEDIA_ROOT}"
        chown -R ${APP_USER}: "${STATIC_ROOT}"
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
