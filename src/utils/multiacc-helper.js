const CryptoJS = require('crypto-js');
const storage = require('node-persist');
const generate = require('generate-api-key');
const adminIdentity = require('./iota/adminIdentity.json')
const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
const ethers = require("ethers")
const ethereum = require("../utils/ethereum/ethereum-config.js")
var fs = require('fs');



function generate_token() {
  const prefix = generate({ length: 15, pool: characters })
  const token = generate({ length: 64, pool: characters, prefix: prefix })
  const salt = generate({ length: 64, pool: characters })

  var split_token = token.split(".");

  const hash = CryptoJS.SHA3(split_token[1] + salt, { outputLength: 256 }).toString(CryptoJS.enc.Hex);

  return { prefix: prefix, token: token, salt: salt, hash: hash }
}

async function check_token(token) {
  if (token == undefined) return false
  var split_token = token.split(".");
  const item = await storage.getItem(split_token[0]);

  if (item == undefined) return false

  const hash = CryptoJS.SHA3(split_token[1] + item.salt, { outputLength: 256 }).toString(CryptoJS.enc.Hex)
  return hash == item.hash
}

async function delete_token(token) {
  const valid_token = await check_token(token)
  if (!valid_token) return false
  var split_token = token.split(".");
  const result = await storage.removeItem(split_token[0])

  return result.removed

}

async function get_acc_data(token) {
  var split_token = token.split(".");
  const data = await storage.getItem(split_token[0])

  return data
}

async function set_acc_data(token, data) {
  var split_token = token.split(".");
  await storage.updateItem(split_token[0], data)
}


async function startSetup() {
  fs.readdir("../routes/.node-persist/storage", async function (err, files) {
    if (err) {
      // throw error?
    } else {
      if (!files.length) {
        //dir empty
        //ask for ETH privatekey on startup?
        const privateKey = "0xdb7bbaee5f30c525a3854958231fe89f0cdbeec09479c769e3d3364f0e666d6a"
        const token_object = generate_token()
        wallet = new ethers.Wallet(privateKey, ethereum.provider)

        const iota_id = adminIdentity.doc.id
        const iota_key = adminIdentity.key.secret

        await storage.init()
        await storage.setItem(token_object.prefix, { salt: token_object.salt, hash: token_object.hash, eth_priv_key: wallet.privateKey, iota_id: iota_id, iota_key: iota_key, iota: { credentials: {} } })
        console.log("Admin token " + token_object.token)
      }
      else {
        //dir not empty
        console.log("Admin user already set")
      }
    }
  });

}

module.exports = {
  generate_token,
  check_token,
  delete_token,
  get_acc_data,
  set_acc_data,
  startSetup
}