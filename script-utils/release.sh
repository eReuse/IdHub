#!/bin/sh

# Propagate new CHANGELOG data to git tag and software roge releases

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

main() {
        cd "$(dirname "$0")/.."

        # get unreleased CHANGELOG
        # awk: if find Match (m) the regex (to next heading) just print that
        CHANGELOG_CONTENT="$(awk '/^# /{if(m)exit; m=1} m' CHANGELOG.md)"

        git tag -a "${VERSION}" --cleanup=verbatim -m "${CHANGELOG_CONTENT}"

        git push origin "${VERSION}"

        # looks like I should wait some seconds, to ensure release works
        sleep 5

        do_codeberg_release
        # TODO do_github_release

        echo "Released ${VERSION}"
}

main "${@:-}"
