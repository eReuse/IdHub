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

inject_env_vars() {
        # related https://www.kenmuse.com/blog/avoiding-dubious-ownership-in-dev-containers/
        if [ -d "${idhub_dir}/.git" ]; then
                git config --global --add safe.directory "${idhub_dir}"
                export COMMIT="commit: $(git log --pretty=format:'%h' -n 1)"
        fi

        cat > status_data <<END
DOMAIN=${DOMAIN}
END
}

deployment_strategy() {
        init_flagfile="${idhub_dir}/already_configured.idhub"

        if [ -f "${init_flagfile}" ]; then
                echo "INFO: detected PREVIOUS deployment"
                ./manage.py migrate
                # warn admin that it should re-enter password to keep the service working
                ./manage.py send_mail_admins
        else
                echo "INFO: detected NEW deployment"
                # this file helps all docker containers to guess number of hosts involved
                #   right now is only needed by new deployment for oidc
                if [ -d "/sharedsecret" ]; then
                        touch /sharedsecret/${DOMAIN}
                fi

                # move the migrate thing in docker entrypoint
                #   inspired by https://medium.com/analytics-vidhya/django-with-docker-and-docker-compose-python-part-2-8415976470cc
                echo "INFO detected NEW deployment"
                ./manage.py migrate

                if [ "${DEMO:-}" = 'true' ]; then
                        printf "This is DEVELOPMENT/PILOTS_EARLY DEPLOYMENT: including demo hardcoded data\n" >&2
                        PREDEFINED_TOKEN="${PREDEFINED_TOKEN:-}"
                        ./manage.py demo_data "${PREDEFINED_TOKEN}"
                fi

                if [ "${OIDC_ORGS:-}" ]; then
                        config_oidc4vp
                else
                        echo "Note: skipping oidc4vp config"
                fi
                touch "${init_flagfile}"
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
                ./manage.py print_settings
        fi

        if [ ! "${DEBUG:-}" = "true" ]; then
                ./manage.py collectstatic
                if [ "${EXPERIMENTAL:-}" = "true" ]; then
                        # reloading on source code changing is a debugging future, maybe better then use debug
                        #   src https://stackoverflow.com/questions/12773763/gunicorn-autoreload-on-source-change/24893069#24893069
                        # gunicorn with 1 worker, with more than 1 worker this is not expected to work
                        gunicorn --access-logfile - --error-logfile - -b :${PORT} trustchain_idhub.wsgi:application
                else
                        ./manage.py runserver 0.0.0.0:${PORT}
                fi
        elif [ "${DEMO:-}" = 'true' ]; then
                VAULT_PASSWORD="DEMO"
                # open_service: automatically unlocks the vault,
                #   and runs the service
                #   useful for debugging/dev/demo purposes ./manage.py
                ./manage.py open_service "${VAULT_PASSWORD}" 0.0.0.0:${PORT}
        else
                ./manage.py runserver 0.0.0.0:${PORT}
        fi
}

check_app_is_there() {
        if [ ! -f "./manage.py" ]; then
                usage
        fi
}

main() {
        idhub_dir='/opt/idhub'
        cd "${idhub_dir}"

        check_app_is_there

        deployment_strategy

        inject_env_vars

        runserver
}

main "${@}"
