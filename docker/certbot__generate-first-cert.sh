#!/bin/sh

set -e
set -u
# DEBUG
set -x

main() {
        cd "$(dirname "${0}")"
        . ../.env
        # inspiration: https://docs.joinpeertube.org/install/docker
        mkdir -p /opt/ereuse-docker-data/${IDHUB_DOMAIN}/certbot
        docker run -it --rm --name certbot-temp -p 80:80 -v "$(pwd)/docker-volume/certbot/conf:/etc/letsencrypt" certbot/certbot certonly --standalone --agree-tos --register-unsafely-without-email -d "${IDHUB_DOMAIN}"
}

main "${@:-}"

# written in emacs
# -*- mode: shell-script; -*-
