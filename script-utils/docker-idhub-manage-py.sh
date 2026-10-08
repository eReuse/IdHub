#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

main() {
        docker compose exec idhub \
               sh -c "gosu \$(cat /app_user) ./manage.py ${*}"
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
