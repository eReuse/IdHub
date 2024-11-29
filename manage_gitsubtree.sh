#!/bin/sh

# SPDX-License-Identifier: AGPL-3.0-or-later

set -e
set -u
# DEBUG
set -x

manage_gitst() {
        path="${1}"
        repo="${2} ${3}"
        if [ ! -d "${path}" ]; then
                action="add"
        else
                action="pull"
        fi
        cmd="git subtree ${action} --prefix ${path} ${repo} --squash"
        ${cmd}
}

main() {
	# right now, just devicehub-teal
	manage_gitst 'devicehub-django' 'https://farga.pangea.org/ereuse/devicehub-django' 'dpp'
}

main "${@}"

# written in emacs
# -*- mode: shell-script; -*-
