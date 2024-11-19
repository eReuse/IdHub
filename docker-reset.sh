#!/bin/sh

# Copyright (c) 2024 Pedro <copyright@cas.cat>
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

        if [ ! -f .env ]; then
                cp -v .env.example .env
                echo "WARNING: .env was not there, .env.example was copied, this only happens once"
        fi
        # remove old database
        sudo rm -vfr ./db/*
        docker compose down -v
        docker compose build
        docker compose up ${detach_arg:-}
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
