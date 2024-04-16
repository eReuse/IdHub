#!/bin/sh

if test -f "./deployed-contracts.json"
then
    echo "Contracts already deployed."
else
    echo "Deploying contracts..."
    npx hardhat run scripts/deploy.js --network test
fi

cp ./artifacts/contracts/DepositDevice.sol/DepositDevice.json ./shared/
cp ./deployed-contracts.json ./shared/
node src/index.js