#!/bin/sh

set -e
set -u
# DEBUG
set -x

main() {
        if [ -f "./deployed-contracts.json" ]; then
                echo "Contracts already deployed."
        else
                echo "Deploying contracts..."
                npx hardhat run scripts/deploy.js --network test
        fi

        shared="./shared/"
        cp ./artifacts/contracts/DepositDevice.sol/DepositDevice.json "${shared}" || ls -lah "${shared}"
        cp ./deployed-contracts.json "${shared}"
        node src/index.js
}

main "${@}"

