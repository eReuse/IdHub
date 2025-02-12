#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

main() {
        cd "$(dirname "${0}")"

        if [ "${DETACH:-}" ]; then
                detach_arg='-d'
        fi

        # remove previous data
        rm -fv shared/*
        # remove registry instances
        rm -fv idIndexApi/data/id_url.json
        # remove cached devices
        rm -fv observerModule/data/devices.json

        # .env is the configuration of the docker compose deployment
        if [ ! -f .env ]; then
                cp -v .env.example .env
                echo "WARNING: .env was not there, .env.example was copied, this only happens once"
        fi

        # remove docker volumes (mapped filesystem mounts are persisted)
        docker compose down -v

        docker compose build
        docker compose up ${detach_arg:-}
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
