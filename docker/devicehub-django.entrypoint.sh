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
        INIT_ORG="${INIT_ORG:-example-org}"
        INIT_USER="${INIT_USER:-user@example.org}"
        INIT_PASSWD="${INIT_PASSWD:-1234}"
        ADMIN='True'
        PREDEFINED_TOKEN="${PREDEFINED_TOKEN:-}"
        # specific dpp env vars
        if [ "${DPP:-}" = 'true' ]; then
                # fill env vars in this docker entrypoint
                wait_for_dpp_shared
                export API_DLT='http://api_connector:3010'
                export API_DLT_TOKEN="$(cat "/shared/${OPERATOR_TOKEN_FILE}")"
                export API_RESOLVER='http://id_index_api:3012'
                # TODO hardcoded
                export ID_FEDERATED='DH1'
                # propagate to .env
                dpp_env_vars="$(cat <<END
API_DLT=${API_DLT}
API_DLT_TOKEN=${API_DLT_TOKEN}
API_RESOLVER=${API_RESOLVER}
ID_FEDERATED=${ID_FEDERATED}
END
)"
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
                # TODO hardcoded http proto and port
                ./manage.py dlt_insert_members "http://${DOMAIN}:8000"
        fi

        # 13. Do a rsync api resolve
        ./manage.py dlt_rsync_members

        # 14. Register a new user to the DLT
        DATASET_FILE='/tmp/dataset.json'
        cat > "${DATASET_FILE}" <<END
{
  "email": "${INIT_USER}",
  "password": "${INIT_PASSWD}",
  "api_token": "${API_DLT_TOKEN}"
}
END
        ./manage.py dlt_register_user "${DATASET_FILE}"
}

config_phase() {
	# TODO review this flag file
        init_flagfile="${program_dir}/already_configured"
        if [ ! -f "${init_flagfile}" ]; then

                # non DL user (only for the inventory)
                ./manage.py add_institution "${INIT_ORG}"
                # TODO: one error on add_user, and you don't add user anymore
                ./manage.py add_user "${INIT_ORG}" "${INIT_USER}" "${INIT_PASSWD}" "${ADMIN}" "${PREDEFINED_TOKEN}"

                if [ "${DPP:-}" = 'true' ]; then
                        # 12, 13, 14
                        config_dpp_part1

                        # cleanup other spnapshots and copy dlt/dpp snapshots
                        # TODO make this better
                        rm example/snapshots/*
                        cp example/dpp-snapshots/*.json example/snapshots/
                fi

                # # 15. Add inventory snapshots for user "${INIT_USER}".
                if [ "${DEMO:-}" = 'true' ]; then
                        /usr/bin/time ./manage.py up_snapshots example/snapshots/ "${INIT_USER}"
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
        git config --global --add safe.directory "${program_dir}"
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
                config_phase
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
        deploy
        runserver
}

main "${@}"
