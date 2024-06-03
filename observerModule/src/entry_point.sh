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

        node index.js
}

main "${@}"
