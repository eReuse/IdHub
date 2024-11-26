#!/bin/sh

set -e
set -u
# DEBUG
set -x

# TODO there is a conflict between two shared vars
#   1. from the original docker compose devicehub-teal
#   2. from the new docker compose that integrates all dpp services
wait_for_dpp_shared() {
        while true; do
                # specially ensure VERAMO_API_CRED_FILE is not empty,
                #   it takes some time to get data in
                OPERATOR_TOKEN_FILE='operator-token.txt'
                if [ -f "/shared/${OPERATOR_TOKEN_FILE}" ] && \
                        [ -f "/shared/create_user_operator_finished" ]; then
                        sleep 5
                        echo "Files ready to process."
                        break
                else
                        echo "Waiting for file in shared: ${OPERATOR_TOKEN_FILE}"
                        sleep 5
                fi
        done
}

# 3. Generate an environment .env file.
# TODO cargar via shared
gen_env_vars() {
        # specific dpp env vars
        if [ "${DPP_MODULE}" = 'y' ]; then
                # docker situation
                if [ -d "${DPP_SHARED:-}" ]; then
                        wait_for_dpp_shared
                        export API_DLT='http://api_connector:3010'
                        export API_DLT_TOKEN="$(cat "/shared/${OPERATOR_TOKEN_FILE}")"
                        export API_RESOLVER='http://id_index_api:3012'
                        # TODO hardcoded
                        export ID_FEDERATED='DH1'
                # .env situation
                else
                        dpp_env_vars="$(cat <<END
API_DLT='${API_DLT}'
API_DLT_TOKEN='${API_DLT_TOKEN}'
API_RESOLVER='${API_RESOLVER}'
ID_FEDERATED='${ID_FEDERATED}'
END
)"
                fi
        fi

        # generate config using env vars from docker
        # TODO rethink if this is needed because now this is django, not flask
        cat > .env <<END
${dpp_env_vars:-}
END
}

handle_federated_id() {

        # devicehub host and id federated checker

        # //getAll queries are not accepted by this service, so we remove them
        EXPECTED_ID_FEDERATED="$(curl -s "${API_RESOLVER%/}/getAll" \
                | jq -r '.url | to_entries | .[] | select(.value == "'"${DEVICEHUB_HOST}"'") | .key' \
                | head -n 1)"

        # if is a new DEVICEHUB_HOST, then register it
        if [ -z "${EXPECTED_ID_FEDERATED}" ]; then
                # TODO better docker compose run command
                cmd="docker compose run --entrypoint= devicehub flask dlt_insert_members ${DEVICEHUB_HOST}"
                big_error "No FEDERATED ID maybe you should run \`${cmd}\`"
        fi

        # if not new DEVICEHUB_HOST, then check consistency

        # if there is already an ID in the DLT, it should match with my internal ID
        if [ ! "${EXPECTED_ID_FEDERATED}" = "${ID_FEDERATED}" ]; then

                big_error "ID_FEDERATED should be ${EXPECTED_ID_FEDERATED} instead of ${ID_FEDERATED}"
        fi

        # not needed, but reserved
        # EXPECTED_DEVICEHUB_HOST="$(curl -s "${API_RESOLVER%/}/getAll" \
        #         | jq -r '.url | to_entries | .[] | select(.key == "'"${ID_FEDERATED}"'") | .value' \
        #         | head -n 1)"
        # if [ ! "${EXPECTED_DEVICEHUB_HOST}" = "${DEVICEHUB_HOST}" ]; then
        #         big_error "ERROR: DEVICEHUB_HOST should be ${EXPECTED_DEVICEHUB_HOST} instead of ${DEVICEHUB_HOST}"
        # fi

}

config_dpp_part1() {
        # 12. Add a new server to the 'api resolver'
        if [ "${ID_SERVICE:-}" ]; then
                handle_federated_id
        else
                # TODO when this runs more than one time per service, this is a problem, but for the docker-reset.sh workflow, that's fine
                # TODO put this in already_configured
                ./manage.py dlt_insert_members "${DEVICEHUB_HOST}"
        fi

        # 13. Do a rsync api resolve
        ./manage.py dlt_rsync_members

        # 14. Register a new user to the DLT
        DATASET_FILE='/tmp/dataset.json'
        cat > "${DATASET_FILE}" <<END
{
  "email": "${EMAIL_DEMO}",
  "password": "${PASSWORD_DEMO}",
  "api_token": "${API_DLT_TOKEN}"
}
END
        ./manage.py dlt_register_user "${DATASET_FILE}"
}

config_phase() {
        init_flagfile='/already_configured'
        if [ ! -f "${init_flagfile}" ]; then

                if [ "${DPP_MODULE}" = 'y' ]; then
                        # 12, 13, 14
                        config_dpp_part1
                fi

                # TODO fix wrong syntax
                # non DL user (only for the inventory)
                #   ./manage.py adduser user2@dhub.com ${PASSWORD_DEMO}

                # # 15. Add inventory snapshots for user "${EMAIL_DEMO}".
                if [ "${IMPORT_SNAPSHOTS}" = 'y' ]; then
                        cp /mnt/snapshots/*.json example/snapshots/
                        /usr/bin/time ./manage.py up_snapshots "${EMAIL_DEMO}" ${PASSWORD_DEMO}
                fi

                # remain next command as the last operation for this if conditional
                touch "${init_flagfile}"
        fi
}

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
        gen_env_vars
        config_phase
        deploy
        runserver
}

main "${@}"
