const DeviceFactory = artifacts.require("DeviceFactory");
const DocumentProofs = artifacts.require("DocumentProofs");
const AddressRoles = artifacts.require("AddressRoles");


module.exports = async function (deployer, network, accounts) {
  // deployment steps
  await deployer.deploy(AddressRoles)
    .then(async function (instance) {
      roles = instance;
      console.log ("role address: " + roles.address)
      await deployer.deploy(DeviceFactory, roles.address)
  })
  await deployer.deploy(DocumentProofs);
};