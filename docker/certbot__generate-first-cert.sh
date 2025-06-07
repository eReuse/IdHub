#!/bin/sh

set -e
set -u
# DEBUG
set -x

main() {
        cd "$(dirname "${0}")"
        . ../.env
        # inspiration: https://docs.joinpeertube.org/install/docker
        mkdir -p ${IDHUB_ROOT_DIR}/${IDHUB_DOCKER_DIR}/${IDHUB_DOMAIN}/certbot
        certbot_vol="${IDHUB_ROOT_DIR}/${IDHUB_DOCKER_DIR}/${IDHUB_DOMAIN}/certbot/conf:/etc/letsencrypt"
        certbot_args="certonly --standalone --agree-tos --register-unsafely-without-email -d ${IDHUB_DOMAIN}"
        docker run -it --rm --name certbot-init -p 80:80 -v "${certbot_vol}" certbot/certbot ${certbot_args}
}

main "${@:-}"

# written in emacs
# -*- mode: shell-script; -*-
