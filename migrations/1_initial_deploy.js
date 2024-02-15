const DeviceFactory = artifacts.require("DeviceFactory");
//const DocumentProofs = artifacts.require("DocumentProofs");
const AccessList = artifacts.require("AccessList");
const EthereumDIDRegistry = artifacts.require("EthereumDIDRegistry")
const TokenContract = artifacts.require("TokenContract")


module.exports = async function (deployer, network, accounts) {
  const abacAddr = "0xb77fD3634e0a4BAc69cd223ad146FE45361b5762"
  await deployer.deploy(TokenContract)
        .then(async function (ins){
          tokens=ins;
          await deployer.deploy(DeviceFactory, abacAddr, tokens.address)
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