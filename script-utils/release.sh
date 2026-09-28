#!/bin/sh

set -e
set -u
# DEBUG
set -x

do_codeberg_release() {
        release_data='{
  "tag_name":"%s",
  "name":"%s",
  "body":"%s",
  "draft":false,
  "prerelease":false,
  "hide_archive_links":true
}'
        codeberg_post_url='https://codeberg.org/api/v1/repos'
        curl -s \
             -X POST "${codeberg_post_url}/${CODEBERG_USER}/${CODEBERG_REPO}/releases" \
             -H "Authorization: token ${CODEBERG_TOKEN}" \
             -H "Content-Type: application/json" \
             -d "$(printf "${release_data}" \
                          "${VERSION}" "${VERSION}" "${release_message}")"
}

get_next_version() {
        current_year="$(date +'%Y')"

        previous_number=$(git tag --list \
                                  | grep "${current_year}\." \
                                  | sed "s/.*${current_year}\.//" \
                                  | sed 's/[^0-9]//g' \
                                  | sort -n \
                                  | tail -1)

        number="$(( ${previous_number:-0} + 1 ))"
        VERSION="v$(echo "${current_year}.${number}")"
}

main(){
        # if [ -n "$(git status --porcelain)" ]; then
        #        echo "You have uncommitted changes in git"
        #        exit 1
        # fi

        cd "$(dirname "$0")/.."

        CHANGELOG_CONTENT="$(python3 ./script-utils/generate-changelog.py)"
        get_next_version

        cat > CHANGELOG.md.new <<EOF
# ${VERSION}

${CHANGELOG_CONTENT}

$(cat CHANGELOG.md)
EOF
        mv CHANGELOG.md.new CHANGELOG.md

        git tag -a "${VERSION}" -m "${CHANGELOG_CONTENT}"

        git push origin "${VERSION}"

        # looks like I should wait some seconds, to ensure release works
        sleep 5

        do_codeberg_release
        # TODO github release

        echo "Released ${VERSION}"
}

main "${@:-}"
