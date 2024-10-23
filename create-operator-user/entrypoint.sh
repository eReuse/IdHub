#!/bin/sh

set -e
set -u
# DEBUG
set -x

main() {
	ADMIN_TOKEN_FILE=api-connector_admin-token.txt
	VERAMO_API_CRED_FILE=veramo-api_credential.json
	while true; do
		# specially ensure VERAMO_API_CRED_FILE is not empty,
		#   it takes some time to get data in
		if [ -f "shared/${ADMIN_TOKEN_FILE}" ] && \
		    [ -f "shared/${VERAMO_API_CRED_FILE}" ] && \
		    ! wc -l "shared/${VERAMO_API_CRED_FILE}" | awk '{print $1;}' | grep -qE '^0$'; then
			sleep 5
			echo "Files ready to process."
			break
		else
			echo "Waiting for files in shared: (1) ${ADMIN_TOKEN_FILE}, (2) ${VERAMO_API_CRED_FILE}"
			sleep 5
		fi
	done

	export ADMIN_TOKEN="$(cat "shared/${ADMIN_TOKEN_FILE}")"
	export VERAMO_API_CRED="$(cat "shared/${VERAMO_API_CRED_FILE}")"
	node scripts/register_user.js > shared/operator-token.txt
	export OPERATOR_TOKEN="$(cat "shared/operator-token.txt")"
	node scripts/call_oracle.js
	node scripts/mint.js
	touch shared/create_user_operator_finished
}

main "${@}"
