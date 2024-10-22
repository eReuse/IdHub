const { ethers } = require("hardhat");
const fs = require('fs');


// Based on: https://ethereum.stackexchange.com/questions/162325/hardhat-get-contract-address-and-pass-as-param-to-another-contract-to-deploy
// npx hardhat run scripts/deploy.js --network hardhat
async function main() {
  // console.log(hardhat)
  // Initialize an empty object to store deployed contract addresses
  let deployedContracts = {};
  let adminAccesList = "0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F"

  let TokenContract, AccessList, DeviceFactory, EthereumDIDRegistry;


  // Deploy the contract
  const TokenContractContractFactory = await ethers.getContractFactory("TokenContract");
  const TokenContractContract = await TokenContractContractFactory.deploy(); // Pass constructor params (if any)

  // Get the address of the deployed contract
  TokenContract = await TokenContractContract.getAddress()


  // Deploy the contract
  const AccessListContractFactory = await ethers.getContractFactory("AccessList");
  const AccessListContract = await AccessListContractFactory.deploy(adminAccesList); // Pass constructor params (if any)

  // Get the address of the deployed contract
  AccessList = await AccessListContract.getAddress();


  // Deploy the contract
  const DeviceFactoryContractFactory = await ethers.getContractFactory("DeviceFactory");
  const DeviceFactoryContract = await DeviceFactoryContractFactory.deploy(AccessList, TokenContract); // Pass constructor params (if any)

  // Get the address of the deployed contract
  DeviceFactory = await DeviceFactoryContract.getAddress();


  // Deploy the contract
  const EthereumDIDRegistryContractFactory = await ethers.getContractFactory("EthereumDIDRegistry");
  const EthereumDIDRegistryContract = await EthereumDIDRegistryContractFactory.deploy(); // Pass constructor params (if any)

  // Get the address of the deployed contract
  EthereumDIDRegistry = await EthereumDIDRegistryContract.getAddress()


  // Store the addresses of the deployed contracts in 'deployedContracts' object
  deployedContracts = {
    TokenContract: TokenContract,
    AccessList: AccessList,
    DeviceFactory: DeviceFactory,
    EthereumDIDRegistry: EthereumDIDRegistry
  }

  // Write the 'deployedContracts' object to 'deployed-contracts.json' file
  fs.writeFileSync('deployed-contracts.json', JSON.stringify(deployedContracts, null, 2));

  console.log("Contracts have been deployed and their contract addresses have been saved to deployed-contracts.json");
}

main()
  .then(() => process.exit(0))
  .catch(error => {
    console.error(error);
    process.exit(1);
  });