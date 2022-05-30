const DeviceFactory = artifacts.require("DeviceFactory");
const DocumentProofs = artifacts.require("DocumentProofs");
const AddressRoles = artifacts.require("AddressRoles");


module.exports = async function (deployer, network, accounts) {
  // deployment steps
  await deployer.deploy(DeviceFactory);
  await deployer.deploy(AddressRoles);
  await deployer.deploy(DocumentProofs);
};