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

        # TODO I can quit the SUDO when I apply the technique I used in idhub docker

        # remove previous data
        sudo rm -fv shared/*
        # remove registry instances
        sudo rm -fv idIndexApi/data/id_url.json
        # remove cached devices
        sudo rm -fv observerModule/data/devices.json

        # .env is the configuration of the docker compose deployment
        if [ ! -f .env ]; then
                cp -v .env.example .env
                echo "WARNING: .env was not there, .env.example was copied, this only happens once"
        fi

        # remove docker volumes (mapped filesystem mounts are persisted)
        docker compose down -v

        docker compose build
        docker compose pull
        docker compose up ${detach_arg:-}
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
