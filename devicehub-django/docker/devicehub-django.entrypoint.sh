#!/bin/sh

set -e
set -u
# DEBUG
set -x

check_app_is_there() {
        if [ ! -f "./manage.py" ]; then
                usage
        fi
}

deploy() {
        # TODO this is weird, find better workaround
        git config --global --add safe.directory /opt/devicehub-django
        export COMMIT=$(git log --format="%H %ad" --date=iso -n 1)

        if [ "${DEBUG:-}" = 'true' ]; then
                ./manage.py print_settings
        else
                echo "DOMAIN: ${DOMAIN}"
        fi

        # detect if existing deployment (TODO only works with sqlite)
        if [ -f "${program_dir}/db/db.sqlite3" ]; then
                echo "INFO: detected EXISTING deployment"
                ./manage.py migrate
        else
                # move the migrate thing in docker entrypoint
                #   inspired by https://medium.com/analytics-vidhya/django-with-docker-and-docker-compose-python-part-2-8415976470cc
                echo "INFO detected NEW deployment"
                ./manage.py migrate
                INIT_ORG="${INIT_ORG:-example-org}"
                INIT_USER="${INIT_USER:-user@example.org}"
                INIT_PASSWD="${INIT_PASSWD:-1234}"
                ADMIN='True'
                PREDEFINED_TOKEN="${PREDEFINED_TOKEN:-}"
                ./manage.py add_institution "${INIT_ORG}"
                # TODO: one error on add_user, and you don't add user anymore
                ./manage.py add_user "${INIT_ORG}" "${INIT_USER}" "${INIT_PASSWD}" "${ADMIN}" "${PREDEFINED_TOKEN}"

                if [ "${DEMO:-}" = 'true' ]; then
                        ./manage.py up_snapshots example/snapshots/ "${INIT_USER}"
                fi
        fi
}

runserver() {
        PORT="${PORT:-8000}"
        if [ "${DEBUG:-}" = 'true' ]; then
                ./manage.py runserver 0.0.0.0:${PORT}
        else
                # TODO
                #./manage.py collectstatic
                true
                if [ "${EXPERIMENTAL:-}" ]; then
                        # TODO
                        # reloading on source code changing is a debugging future, maybe better then use debug
                        #   src https://stackoverflow.com/questions/12773763/gunicorn-autoreload-on-source-change/24893069#24893069
                        # gunicorn with 1 worker, with more than 1 worker this is not expected to work
                        #gunicorn --access-logfile - --error-logfile - -b :${PORT} trustchain_idhub.wsgi:application
                        true
                else
                        ./manage.py runserver 0.0.0.0:${PORT}
                fi
        fi
}

main() {
        program_dir='/opt/devicehub-django'
        cd "${program_dir}"
        deploy
        runserver
}

main "${@}"
