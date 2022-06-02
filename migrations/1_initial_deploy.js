const DeviceFactory = artifacts.require("DeviceFactory");
const DocumentProofs = artifacts.require("DocumentProofs");
const AccessList = artifacts.require("AccessList");


module.exports = async function (deployer, network, accounts) {
  // deployment steps
  await deployer.deploy(AccessList)
    .then(async function (instance) {
      roles = instance;
      console.log ("role address: " + roles.address)
      await deployer.deploy(DeviceFactory, roles.address)
  })
  await deployer.deploy(DocumentProofs);
};