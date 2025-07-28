#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

main() {
        cd "$(dirname "${0}")"
        if [ ! -f .env ]; then
                echo "Detected .env file is missing, so let's initialize the config"
                cp -v .env.example .env
        fi
        . ./.env

        VIDEO="${VIDEO:-no}"
        browser="${browser:-firefox}"
        project="${project:-firefox}"
        headed="${headed:---headed}"

        if [ "${VIDEO}" = 'y' ]; then
                export VIDEO
        else
                unset VIDEO
        fi

        if [ $# -eq 0 ]; then
                npx playwright test --project "${project}" "${headed}"
        else
                #Runs playwright with specific file if provided
                #ej. ./run "tests/lots.spec.ts"
                for test_file in "$@"; do
                        npx playwright test "${test_file}" --project "${project}" "${headed}"
                done
        fi
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
