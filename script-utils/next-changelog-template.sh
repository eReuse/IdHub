#!/bin/sh

# Facilitate data for next changelog

set -e
set -u
# DEBUG
# set -x

get_next_version() {
        current_year="$(date +'%Y')"
        previous_number=$(git tag --list \
                                  | grep "${current_year}" \
                                  | sed "s/v${current_year}\.//" \
                                  | sort -n \
                                  | tail -1)
        number="$(( ${previous_number:-0} + 1 ))"
        VERSION="v$(echo "${current_year}.${number}")"
}

next_changelog() {
        CHANGELOG_CONTENT="$(python ./script-utils/generate-changelog-merge-detail-TEMP.py | grep farga)"
        get_next_version

        cat <<EOF
# ${VERSION}

## Highlights

TODO add manually

## More details

Merged PRs

<details>

${CHANGELOG_CONTENT}

</details>

Full Changelog: https://github.com/eReuse/IdHub/commits/${VERSION}

EOF
}

main() {
        cd "$(dirname "$0")/.."

        next_changelog
}

main "${@:-}"
