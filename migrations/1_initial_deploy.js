const DeviceFactory = artifacts.require("DeviceFactory");
//const DocumentProofs = artifacts.require("DocumentProofs");
const AccessList = artifacts.require("AccessList");
const EthereumDIDRegistry = artifacts.require("EthereumDIDRegistry")


module.exports = async function (deployer, network, accounts) {
  const adminAccesList = "0x2851e010738422CE8786D9F86e166Fc6E1030a1a"
  const abacAddr = "0xacf2fAd56434D48Ca75238614FF49710d72ae982"
  await deployer.deploy(DeviceFactory, abacAddr)
  // await deployer.deploy(AccessList, adminAccesList)
  //   .then(async function (instance) {
  //     roles = instance;
  //     console.log ("role address: " + roles.address)
  //     await deployer.deploy(DeviceFactory, roles.address)
  // })
  await deployer.deploy(EthereumDIDRegistry)
  //await deployer.deploy(DocumentProofs);
};