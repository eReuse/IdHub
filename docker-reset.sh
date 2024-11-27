#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
#set -x

main() {
	cd "$(dirname "${0}")"

        if [ "${DETACH:-}" ]; then
                detach_arg='-d'
        fi

	# remove previous data
	rm -f shared/*
	# remove registry instances
	rm -f idIndexApi/data/id_url.json
	# remove cached devices
	rm -f observerModule/data/devices.json
        # remove old devicehub-django database
        rm -vfr ./devicehub-django/db/*

	# remove docker volumes (mapped filesystem mounts are persisted)
        docker compose down -v

        docker compose build
        docker compose up ${detach_arg:-}
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
