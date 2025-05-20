!/bin/sh

# Copyright (c) 2025 Pedro <copyright@cas.cat>
# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

main() {
        . ../.env
        # inspiration: https://docs.joinpeertube.org/install/docker
        mkdir -p /opt/ereuse-docker-data/${IDHUB_DOMAIN}/certbot
        docker run -it --rm --name certbot-temp -p 80:80 -v "$(pwd)/docker-volume/certbot/conf:/etc/letsencrypt" certbot/certbot certonly --standalone
}

main "${@:-}"

# written in emacs
# -*- mode: shell-script; -*-
