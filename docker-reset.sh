#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

prompt_env_var() {
        # Prompt for an env var if unset or empty, with a fallback default.
        # Usage: prompt_env_var VAR_NAME DEFAULT_VALUE

        var_name="${1}"
        default="${2}"
        info="${3:-}"

        # dereference: get current value of the variable named in $var_name
        eval "current=\${${var_name}:-}"

        if [ -z "${current}" ]; then
                if [ "${info}" ]; then
                        info="\n[${var_name}] info:\n${info}\n"
                fi
                # show the default in the prompt
                printf "${info}\n+ Enter value for %s (default is \"%s\"): " "${var_name}" "${default}"
                # read into a temporary
                read answer
                # if they just hit enter, use default
                if [ -z "${answer}" ]; then
                        answer=${default}
                fi
                # export the result back into the named variable
                export "${var_name}"="${answer}"
        fi
}

# TODO move export from prompt_env_var here to detect empty vars?
add_env_var() {
        # add env var to template
        var_name="${1}"
        template_env_vars="${template_env_vars} \${${var_name}}"
}

use_env_var() {
        # prompt env var for completion, and add env var to template

        var_name="${1}"
        default="${2}"
        info="${3:-}"
        prompt_env_var "${var_name}" "${default}" "${info}"
        add_env_var "${var_name}"
}

docker_wizard() {
        set +x
        printf "\nDetected .env file is missing, so let's initialize the config (if you
want to see again, remove .env file)\n\nPress enter to continue... "
        read enter

        template_env_vars=''
        use_env_var APP_DOMAIN_REQUEST "dpp-dsg.example.org"

        set -x

        # adapt docker user to your runtime needs -> src https://denibertovic.com/posts/handling-permissions-with-docker-volumes/
        #   via https://github.com/moby/moby/issues/22258#issuecomment-293664282
        #   related https://github.com/moby/moby/issues/2259
        export APP_LOCAL_USER_ID_REQUEST="$(id -u "${USER}")"
        add_env_var APP_LOCAL_USER_ID_REQUEST

        # if user is root, place it in /opt
        if [ "${APP_LOCAL_USER_ID_REQUEST}" = 0 ]; then
                export APP_ROOT_DIR_REQUEST='/opt'
        else
                export APP_ROOT_DIR_REQUEST="${HOME}"
        fi
        add_env_var APP_ROOT_DIR_REQUEST

        # src https://stackoverflow.com/questions/41298963/is-there-a-function-for-generating-settings-secret-key-in-django
        export IDHUB_SECRET_KEY_REQUEST="$(python3 -c 'import secrets; print(secrets.token_hex(100))')"
        add_env_var IDHUB_SECRET_KEY_REQUEST

        use_env_var RPROXY_FAKE_HTTP_CERT_REQUEST "true" "use false to use automatic letsencrypt HTTP Cert in the reverse proxy"

        envsubst "${template_env_vars}" < .env.example > .env

        if [ "${RPROXY_FAKE_HTTP_CERT_REQUEST}" = "false" ] ; then
                echo "letsencrypt docker use detected, you should run ./docker/certbot__generate-first-cert.sh before continuing"
                ./docker/certbot__generate-first-cert.sh
        fi
}

# why temp? TODO I can quit the SUDO when I apply the technique I used in idhub docker
temp_remove_data() {
        # remove previous data
        sudo rm -fv shared/*
        # remove registry instances
        sudo rm -fv idIndexApi/data/id_url.json
        # remove cached devices
        sudo rm -fv observerModule/data/devices.json

        # remove docker volumes (mapped filesystem mounts are persisted)
        docker compose down -v
}

main() {
        clear
        cd "$(dirname "${0}")"

        if [ ! -f .env ]; then
                docker_wizard
        fi
        . ./.env

        if [ "${DETACH:-}" ]; then
                detach_arg='-d'
        fi

        temp_remove_data

        docker compose build
        docker compose pull
        docker compose up ${detach_arg:-}
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
