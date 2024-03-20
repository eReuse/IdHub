const DeviceFactory = artifacts.require("DeviceFactory");
//const DocumentProofs = artifacts.require("DocumentProofs");
const AccessList = artifacts.require("AccessList");
const EthereumDIDRegistry = artifacts.require("EthereumDIDRegistry")
const TokenContract = artifacts.require("TokenContract")


module.exports = async function (deployer, network, accounts) {
  const adminAccesList = "0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F"
  var tokens
  var roles
  await deployer.deploy(TokenContract)
    .then(async function (ins) {
      tokens = ins;
      await deployer.deploy(AccessList, adminAccesList)
        .then(async function (instance) {
          roles = instance;
          console.log("role address: " + roles.address)
          await deployer.deploy(DeviceFactory, roles.address)
        })
    })
  // await deployer.deploy(AccessList, adminAccesList)
  //   .then(async function (instance) {
  //     roles = instance;
  //     console.log ("role address: " + roles.address)
  //     await deployer.deploy(DeviceFactory, roles.address)
  // })
  await deployer.deploy(EthereumDIDRegistry)
  //await deployer.deploy(DocumentProofs);
};