# Trublo multi DLT API and solidity contracts


# About The Project

This repository contains a set of solidity smart contracts developed to manage electronic devices and its Product Passport and an API that can call three different DLTs: IOTA, OBADA and a standard private ethereum blockchain.

### [Contracts](contracts)
Main contracts:
- [AccessList](contracts/AccessList.sol): Manages user roles.
- [DeviceFactory](contracts/DeviceFactory.sol): creates devices (contract instances) and keeps track of their location.
- [DepositDevice](contracts/DepositDevice.sol): device instance contract. Keeps track of the actions performed on a single device.

### [API](src)
API that acts as an interface to interact with the smart contracts.
Calls defined inside three different files, [devices](src/routes/devices.js), [credentials](src/routes/credentials.js) and [api_management](src/routes/api_management.js).

## Usage

### Smart contracts deployment
Compile contracts:
```javascript
$npm install
$node_modules/.bin/truffle compile --all --reset
```

Deploy contracts to a desired network (defined inside [truffle-config.js](truffle-config.js)):
```javascript
$node_modules/.bin/truffle migrate --network <network_name> --reset
```

### API deployment
Build and run the docker image (it will deploy the smart contracts by default to the iota-ebsi stable network):
```javascript
$docker-compose up
```

## Other notable files
- [truffle-config.js](truffle-config.js): can define several truffle settings. Mainly used to define blockchain nodes to where contracts will be deployed.
- [demo](demo_eel): demo client to test API calls.
- [migrations](migrations): scripts that define how contracts will be migrated to a network.
- [uml](uml): uml class diagram generated with the "sol2uml" tool.
