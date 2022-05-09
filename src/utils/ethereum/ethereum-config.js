const ethers = require("ethers")

const DeviceFactory = require('../../../build/contracts/DeviceFactory.json');
//457
const DEVICEFACTORY_ADDRESS = DeviceFactory.networks['5777'].address;

//const privateKey = "0c59d9a51420d950c5bf1ee3e52114f2be893680e432a95038b179e3b6e9d0e6"
const privateKey = "765159de24c5bd2abfbd8c95aba6ee84e35b62a22e39338f3b1a71e0145fab09"

const deviceFactoryIface = new ethers.utils.Interface(
  require('../../../build/contracts/DeviceFactory.json').abi
)
const depositDeviceIface = new ethers.utils.Interface(
  require('../../../build/contracts/DepositDevice.json').abi
)

const provider = new ethers.providers.JsonRpcProvider(
  //"HTTP://10.1.3.30:8545"
  "HTTP://127.0.0.1:7545"
)

const signer = new ethers.Wallet(privateKey, provider)
const defaultDeviceFactoryContract = new ethers.Contract(
  DEVICEFACTORY_ADDRESS,
  require('../../../build/contracts/DeviceFactory.json').abi,
  signer
)
module.exports = {
  DEVICEFACTORY_ADDRESS: DEVICEFACTORY_ADDRESS,
  deviceFactoryIface: deviceFactoryIface,
  depositDeviceIface: depositDeviceIface,
  provider: provider,
  signer: signer,
  defaultDeviceFactoryContract: defaultDeviceFactoryContract
}