#!/bin/sh
while true; do
    if test -f "../shared/DepositDevice.json"
    then
        echo "Compiled contract available."
        break
    else
        echo "Waiting for contract deployment..."
        sleep 1
    fi
done

node index.js