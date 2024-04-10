require("@nomicfoundation/hardhat-ethers");
module.exports = {
  networks:{
    hardhat:{
      chainId: 457,
      gasPrice:0,
      hardfork: "london",
      initialBaseFeePerGas:0,
    },
    test: {
      url: "http://localhost:8545",
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
