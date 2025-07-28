#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

# detect inconsistency between tag and branch
#   (it should be the same)
_check_tag() {
        local var_name="${1}"
        local branch_tag="${2}"
        eval local env_tag=\$$var_name

        # exception, stable tag is for main branch
        if [ "${env_tag}" = "stable" ]; then
                env_tag=main
        fi

        if [ "${branch_tag}" != "${env_tag}" ]; then
                set +x
                printf "ERROR: ABORTED: mismatch between:\n"
                printf "%-20s %-25s %s\n" "var" "value" "location"
                printf "%-20s %-25s %s\n" "branch tag" "${branch_tag}" "retrieved from git branch"
                printf "%-20s %-25s %s\n" "${var_name}" "${env_tag}" "retrieved from .env env vars file"
                set -x
                exit 1
        fi
}

_proc() {
        name="${1}"

        . ./.env
        _check_tag 'IDHUB_DOCKER_TAG' "${branch}"

        registry_url="ghcr.io/ereuse/${name}:${tag}"
        docker compose build ${name}
        docker push "${registry_url}"
}

main() {
        cd "$(dirname "${0}")"
        cd ..

        branch="$(git branch --show-current)"
        tag="${tag:-$branch}"

        # TODO hardcoded
        main_branch="main"

        if [ "${tag}" = "${main_branch}" ]; then
                tag='stable'
        fi

        _proc idhub
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
