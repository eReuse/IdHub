#!/bin/sh

set -e
set -u
# DEBUG
set -x

main() {
	OPERATOR_TOKEN_FILE='operator-token.txt'
	while true; do
		# specially ensure VERAMO_API_CRED_FILE is not empty,
		#   it takes some time to get data in
		if [ -f "shared/${OPERATOR_TOKEN_FILE}" ]; then
			sleep 5
			echo "Files ready to process."
			break
		else
			echo "Waiting for files in shared: ${OPERATOR_TOKEN_FILE}"
			sleep 5
		fi
	done

	export REACT_APP_CONNECTOR_API_TOKEN="$(cat "shared/${OPERATOR_TOKEN_FILE}")"

	npm start
}

main "${@}"
