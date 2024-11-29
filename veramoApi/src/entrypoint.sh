#!/bin/sh

set -e
set -u
# DEBUG
set -x

main() {
        while true; do
                if [ -f "../shared/DepositDevice.json" ]; then
                        echo "Compiled contract available."
                        break
                else
                        echo "Waiting for api-connector contract deployment..."
                        sleep 5
                fi
        done

	# TODO hardcoded path
	export ETH_REGISTRY="$(cat ../shared/deployed-contracts.json | jq -r .EthereumDIDRegistry)"
	npx tsx scripts/import-identifier.ts
	python scripts/pyvckit_sign.py > ../shared/pyvckit-api_credential.json
        node index.js
}

main "${@}"
