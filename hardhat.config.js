require("@nomicfoundation/hardhat-ethers");
const { vars } = require("hardhat/config");
const TEST_NODE_IP=vars.get("TEST_NODE_IP", "blockchain_test_node")
const miningInterval = parseInt(process.env.MINING_INTERVAL, 10) || 1000;

module.exports = {
  networks:{
    hardhat:{
      chainId: 457,
      gasPrice:0,
      hardfork: "london",
      initialBaseFeePerGas:0,
      mining: {
          auto: false,
          interval: miningInterval,
      },
    },
    test: {
      url: "http://"+TEST_NODE_IP+":8545",
      accounts: {
        mnemonic: "discover angle erosion trap barrel wage chest drop one raven tray degree",
        path: "m/44'/60'/0'/0",
        initialIndex: 0,
        count: 20,
        passphrase: "",
      },
      chainId: 457,
      gasPrice: 0
    },
    abc2_besu: {
      url: "http://45.150.187.30:8545",
      accounts: {
        mnemonic: "discover angle erosion trap barrel wage chest drop one raven tray degree",
        path: "m/44'/60'/0'/0",
        initialIndex: 0,
        count: 20,
        passphrase: "",
      },
      chainId: 457,
      gasPrice: 0
    }
  },
  solidity: {
    version: "0.8.24",
    settings: {
      viaIR: true,
      optimizer: {
        enabled: true,
        //runs: 1500
      },
      evmVersion: "london"
    },
  },
};
