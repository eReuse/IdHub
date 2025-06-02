const ethers = require("ethers")
const DeviceFactory = require('../../../artifacts/contracts/DeviceFactory.sol/DeviceFactory.json');

const TokenContract = require('../../../artifacts/contracts/TokenContract.sol/TokenContract.json');

const AccessList = require('../../../artifacts/contracts/AccessList.sol/AccessList.json');

const DepositDevice = require('../../../artifacts/contracts/DepositDevice.sol/DepositDevice.json');

const deployedContracts = require('../../../deployed-contracts.json')

const process = require("process")

const dotenv = require('dotenv');
dotenv.config();

// const privateKey = "765159de24c5bd2abfbd8c95aba6ee84e35b62a22e39338f3b1a71e0145fab09"
const privateKey = process.env.ETH_PRIV_KEY

//TODO: cambiar a environment (besu client variable, nodeIP y privKey)
const nodeIP = process.env.NODE_IP
const ethClient = process.env.ETH_CLIENT

const idIndexURL = process.env.ID_INDEX

const chainId = process.env.CHAIN_ID.toString()
console.log(chainId)

const DEVICEFACTORY_ADDRESS = deployedContracts.DeviceFactory;
const ACCESSLIST_ADDRESS = deployedContracts.AccessList;
const TOKEN_CONTRACT_ADDRESS = deployedContracts.TokenContract;

const veramoURL = process.env.VERAMO_URL



const deviceFactoryIface = new ethers.Interface(
  DeviceFactory.abi
)
const accessListIface = new ethers.Interface(
  AccessList.abi
)
const depositDeviceIface = new ethers.Interface(
  DepositDevice.abi
)
const tokenContractIface = new ethers.Interface(
  TokenContract.abi
)


const provider = new ethers.JsonRpcProvider(
  nodeIP
  //"HTTP://127.0.0.1:7545"
)

const signer = new ethers.Wallet(privateKey, provider)
const defaultDeviceFactoryContract = new ethers.Contract(
  DEVICEFACTORY_ADDRESS,
  DeviceFactory.abi,
  signer
)

const defaultAccessListContract = new ethers.Contract(
  ACCESSLIST_ADDRESS,
  AccessList.abi,
  signer
)


module.exports = {
  DeviceFactory: DeviceFactory,
  TokenContract: TokenContract,
  AccessList: AccessList,
  DepositDevice: DepositDevice,
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
  nodeIP: nodeIP,
  idIndexURL: idIndexURL,
  TOKEN_CONTRACT_ADDRESS: TOKEN_CONTRACT_ADDRESS,
  tokenContractIface: tokenContractIface,
  veramoURL: veramoURL,
  chainId: chainId
}
