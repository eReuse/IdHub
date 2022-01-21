# Trublo contracts and API

### [Contracts](contracts)
Main contracts:
- [DeviceFactory](contracts/DeviceFactory.sol): creates devices (contract instances) and keeps track of their location.
- [DepositDevice](contracts/DepositDevice.sol): device instance contract. Keeps track of the actions performed on a single device.

### [API](src)
API that acts as an interface to interact with the smart contracts.
Calls defined inside [this file](src/routes/devices.js).

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
Build and run the docker image:
```javascript
$docker-compose up
```

## Other notable files
- [truffle-config.js](truffle-config.js): can define several truffle settings. Mainly used to define blockchain nodes to where contracts will be deployed.
- [demo.js](demo.js): demo console client to test API calls.
- [migrations](migrations): scripts that define how contracts will be migrated to a network.
