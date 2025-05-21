#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

remove_data() {
        docker compose down -v

        if [ "${IDHUB_DB_TYPE}" = "postgres" ]; then
                # then remove data and directories
                docker run --rm -u 999 -v "/opt/ereuse-docker-data/${IDHUB_DOMAIN}/idhub-postgres:/data" alpine sh -c "rm -rf /data/*"
        else
                rm -f "./db.sqlite3"
        fi
}

# Prompt for an env var if unset or empty, with a fallback default.
# Usage: prompt_env_var VAR_NAME DEFAULT_VALUE
prompt_env_var() {
        set +x
        var_name=${1}
        default=${2}
        info=${3:-}

        # dereference: get current value of the variable named in $var_name
        eval "current=\${${var_name}:-}"

        if [ -z "${current}" ]; then
                # show the default in the prompt
                printf "${info}Enter value for %s (default is %s): " "${var_name}" "${default}"
                # read into a temporary
                read answer
                # if they just hit enter, use default
                if [ -z "${answer}" ]; then
                        answer=${default}
                fi
                # export the result back into the named variable
                export "${var_name}"="${answer}"
        fi
        set -x
}

main() {
        cd "$(dirname "${0}")"

        if [ ! -f .env ]; then
                prompt_env_var IDHUB_DOMAIN_REQUEST "idhub.example.org"
                # TODO add more useful vars (postfix _REQUEST)
                #   - db persistence
                #   - db type
                #   - docker profile
                envsubst '${IDHUB_DOMAIN_REQUEST}' < .env.example > .env
                #cp -v .env.example .env
                echo "WARNING: .env was not there, .env.example was copied, this only happens once"
        fi
        . ./.env

        remove_data

        if [ "${DEV_DOCKER_ALWAYS_BUILD:-}" = 'true' ]; then
                docker compose build
        fi
        docker compose up ${detach_arg:-}
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
