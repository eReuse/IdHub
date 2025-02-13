# Ereuse DPP


# About The Project

This repository contains a set of solidity smart contracts developed to manage electronic devices and its Product Passport and an API that can call a IOTA L2 DLT with smart contracts.

### [Contracts](contracts)
Main contracts:
- [DeviceFactory](contracts/DeviceFactory.sol): creates devices (contract instances) and keeps track of their location.
- [DepositDevice](contracts/DepositDevice.sol): device instance contract. Keeps track of the actions performed on a single device.
- [TokenContract](contracts/TokenContract.sol): manages an ERC20 token for Extended Producer Responsibility (EPR) from manufacturers to recyclers.

### [Connector HTTP API](src)
HTTP API for device inventory service instances (such as DeviceHub) that report proof events. It acts as an interface to interact with smart contracts managing a verifiable registry about product items, DPPs, changes, actors and deposits.
Calls defined inside two different files, [devices](src/routes/devices.js), and [api_management](src/routes/api_management.js).

### [DID resolver (ereuse method)](didResolverApi)
HTTP API that resolves ereuse DIDs representing a centain device into its DID document.

### [ID index API](idIndexApi)
HTTP API that registers and resolves device inventory instance's IDs to URLs.

### [DPP indexer](observerModule)
Indexes DPP information listening to events from the smart contracts. It also implements an HTTP API to provide fuzzy text search on the indexed data.

### [DPP search engine](searchEngine)
Web based DPP search engine.

## Deployment order
Follow each README:
1. [ID index API](idIndexApi)
2. [Contracts](contracts)
3. [Connector HTTP API](src)
4. [DID resolver (ereuse method)](didResolverApi)
5. [DPP indexer](observerModule)
6. [DPP search engine](searchEngine)

## Deployment and configuration (Contracts and Connector HTTP API)

### Configuration parameters (Connector HTTP API)
Edit the [.env](src/.env) file. Default data :

- ETH_CLIENT=iota_evm
- ETH_PRIV_KEY=807118c237e01677f0522f9ca50535b1984481ea2e09115197934a9cd73ab8c1
- NODE_IP=https://json-rpc.evm.stable.iota-ec.net
- CHAIN_ID=1074
- ID_INDEX=[ID index api url]

The ETH_PRIV_KEY should have enough funds (ETH) to work.

### Manual deployment

Compile contracts:
```javascript
npm install
node_modules/.bin/truffle compile --all --reset
```

Deploy contracts to a desired network (defined inside [truffle-config.js](truffle-config.js)). For the IOTA stable network, use "iota_stable":
```javascript
node_modules/.bin/truffle migrate --network <network_name> --reset
```

Start the API:
```javascript
cd src
node index.js
```

### Docker deployment

Build and run the docker image, we recommend using the buildx and docker-compose plugins (debian packages: `docker-compose-plugin` and `docker-buildx-plugin`). It will deploy the smart contracts by default to the iota-ebsi stable network, the DID resolver and the HTTP API:

```sh
./docker-reset.sh
```

The API will run on port 3010 and the DID resolver on port 3011.

## Other notable files
- [truffle-config.js](truffle-config.js): can define several truffle settings. Mainly used to define blockchain nodes to where contracts will be deployed.
- [demo](demo_eel): demo client to test API calls (some features may be outdated).
- [migrations](migrations): scripts that define how contracts will be migrated to a network.
- [Python lib](pythonPackage): Python library to interact with the API. Most recent version at https://test.pypi.org/project/ereuseapitest/
