const DeviceFactory = artifacts.require("DeviceFactory");
const DocumentProofs = artifacts.require("DocumentProofs");


module.exports = async function (deployer, network, accounts) {
  // deployment steps
  await deployer.deploy(DeviceFactory);
  await deployer.deploy(DocumentProofs);
};