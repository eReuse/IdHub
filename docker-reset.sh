#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

main() {
        cd "$(dirname "${0}")"

        rm -fv ./db.sqlite3
        if [ ! -f .env ]; then
                cp -v .env.example .env
                echo "WARNING: .env was not there, .env.example was copied, this only happens once"
        fi
        
        docker compose down -v
        if [ "${DEV_DOCKER_ALWAYS_BUILD:-}" = 'true' ]; then
                docker compose build
        fi
        docker compose up ${detach_arg:-}

        # TODO docker registry
        #project=dkr-dsg.ac.upc.edu/trustchain-oc1-orchestral
        #idhub_image=${project}/idhub:${idhub_tag}
        #idhub_branch=$(git -C IdHub branch --show-current)
        # docker build -f docker/idhub.Dockerfile -t ${idhub_image} -t ${project}/idhub:${idhub_branch}__latest .
        #docker tag hello-world:latest farga.pangea.org/pedro/test/hello-world
        #docker push farga.pangea.org/pedro/test/hello-world:latest
}

main "${@}"

# written in emacs
# -*- mode: shell-scrip; -*-t
