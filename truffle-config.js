const HDWalletProvider = require("@truffle/hdwallet-provider");

module.exports = {
  networks: {
    development: {
      host: "127.0.0.1",     // Localhost (default: none)
      port: 7545,            // Standard Ethereum port (default: none)
      network_id: "5777",       // Any network (default: none) 5777
    },
    abc2: {
      host: "10.1.3.30",
      port: 8545,
      network_id: 456,
      gasPrice: 0,
      gas: 8000000,
    },
    abc2_besu: {
      provider: () =>
        new HDWalletProvider({
          mnemonic: {
            phrase: "discover angle erosion trap barrel wage chest drop one raven tray degree"
          },
          providerOrUrl: "http://10.1.3.30:8545",
        }),
      network_id: 457,
      gasPrice: 0
    },
    test1: {
      //networkCheckTimeout: 99999999,
      provider: () =>
        new HDWalletProvider({
          mnemonic: {
            phrase: "plastic pilot subject deliver mechanic deliver fetch lend recall faith problem harbor"
          },
          providerOrUrl: "http://127.0.0.1:8545",
        }),
      network_id: 458,
      gasPrice: 0,
    },
    alastriaT: {
      gasPrice: 0x0,
      provider: () => {
        return new HDWalletProvider("plastic pilot subject deliver mechanic deliver fetch lend recall faith problem harbor",
          "http://10.1.1.41:22000");
      },
      network_id: "83584648538",
    },
  },
  compilers: {
    solc: {
      version: "^0.8.17",
      settings: {
        optimizer: {
          enabled: true,
          //runs: 1500
        },
        evmVersion: "london"
      }
    }
  }
};