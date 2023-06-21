const ethers = require("ethers")
const DeviceFactory = require('../../../build/contracts/DeviceFactory.json');
//457
const DEVICEFACTORY_ADDRESS = DeviceFactory.networks['1074'].address;

const AccessList = require('../../../build/contracts/AccessList.json');
const ACCESSLIST_ADDRESS = AccessList.networks['1074'].address;
const process = require("process")

const dotenv = require('dotenv');
dotenv.config();

// const privateKey = "765159de24c5bd2abfbd8c95aba6ee84e35b62a22e39338f3b1a71e0145fab09"
const privateKey = process.env.ETH_PRIV_KEY

//TODO: cambiar a environment (besu client variable, nodeIP y privKey)
const nodeIP = process.env.NODE_IP
const ethClient = process.env.ETH_CLIENT



const deviceFactoryIface = new ethers.utils.Interface(
  require('../../../build/contracts/DeviceFactory.json').abi
)
const accessListIface = new ethers.utils.Interface(
  require('../../../build/contracts/AccessList.json').abi
)
const depositDeviceIface = new ethers.utils.Interface(
  require('../../../build/contracts/DepositDevice.json').abi
)

// const provider = new ethers.providers.JsonRpcProvider(
const provider = new ethers.providers.WebSocketProvider(
  nodeIP
  //"HTTP://127.0.0.1:7545"
)

const signer = new ethers.Wallet(privateKey, provider)
const defaultDeviceFactoryContract = new ethers.Contract(
  DEVICEFACTORY_ADDRESS,
  require('../../../build/contracts/DeviceFactory.json').abi,
  signer
)

const defaultAccessListContract = new ethers.Contract(
  ACCESSLIST_ADDRESS,
  require('../../../build/contracts/AccessList.json').abi,
  signer
)


module.exports = {
  DEVICEFACTORY_ADDRESS: DEVICEFACTORY_ADDRESS,
  ACCESSLIST_ADDRESS: ACCESSLIST_ADDRESS,
  deviceFactoryIface: deviceFactoryIface,
  accessListIface: accessListIface,
  depositDeviceIface: depositDeviceIface,
  provider: provider,
  signer: signer,
  defaultDeviceFactoryContract: defaultDeviceFactoryContract,
  defaultAccessListContract: defaultAccessListContract,
  ethClient: ethClient,
  nodeIP: nodeIP
}
