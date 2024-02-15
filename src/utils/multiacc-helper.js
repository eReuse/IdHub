const CryptoJS = require('crypto-js');
const storage = require('node-persist');
// const generate = require('generate-api-key');
const adminIdentity = require('./iota/adminIdentity.json')
const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
const ethers = require("ethers")
const ethereum = require("../utils/ethereum/ethereum-config.js");
const { setMask } = require('readline-sync');

function generate(length) {
  let res = ""
  let char_length = characters.length
  for(var i = 0; i<length; i++) {
    res+=characters.charAt(Math.floor(Math.random()*char_length))
  }
  return res
}

function generate_token() {
  // const prefix = generate({ length: 15, pool: characters })
  // const token = generate({ length: 64, pool: characters, prefix: prefix })
  // const salt = generate({ length: 64, pool: characters })

  // var split_token = token.split(".");
  const prefix = generate(15)
  const token = generate(64)
  const salt = generate(64)

  const hash = CryptoJS.SHA3(token + salt, { outputLength: 256 }).toString(CryptoJS.enc.Hex);
  // const hash = CryptoJS.SHA3(split_token[1] + salt, { outputLength: 256 }).toString(CryptoJS.enc.Hex);

  return { prefix: prefix, token: prefix + "." + token, salt: salt, hash: hash }
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


async function set_admin() {
  // fs.readdir("../routes/.node-persist/storage", async function (err, files) {
  //   if (err) {
  //     // throw error?
  //   } else {
  //     if (!files.length) {
  //       //dir empty
  //       //ask for ETH privatekey on startup?
  //       const privateKey = "0xdb7bbaee5f30c525a3854958231fe89f0cdbeec09479c769e3d3364f0e666d6a"
  //       const token_object = generate_token()
  //       wallet = new ethers.Wallet(privateKey, ethereum.provider)

  //       const iota_id = adminIdentity.doc.id
  //       const iota_key = adminIdentity.key.secret

  //       await storage.init()
  //       await storage.setItem(token_object.prefix, { salt: token_object.salt, hash: token_object.hash, eth_priv_key: wallet.privateKey, iota_id: iota_id, iota_key: iota_key, iota: { credentials: {} } })
  //       console.log("Admin token " + token_object.token)
  //     }
  //     else {
  //       //dir not empty
  //       console.log("Admin user already set")
  //     }
  //   }
  // });

  const admin_object = await storage.getItem("admin")
  if (admin_object == undefined) {
    console.log("Setting admin user...")
    const privateKey = "0x807118c237e01677f0522f9ca50535b1984481ea2e09115197934a9cd73ab8c1"
    const token_object = generate_token()
    const wallet = new ethers.Wallet(privateKey, ethereum.provider)

    // const send_eth_tx={
    //   from: ethereum.signer.address,
    //   to: "0x2851e010738422CE8786D9F86e166Fc6E1030a1a",
    //   value: ethers.utils.parseEther("1"),
    //   nonce: ethereum.provider.getTransactionCount(ethereum.signer.address, "latest"),
    //   gasLimit: ethers.utils.hexlify(50000),
    //   gasPrice: 0
    // }
    
    // let res_eth = await ethereum.signer.sendTransaction(send_eth_tx)

    // const iota_id = adminIdentity.doc.id
    // const iota_key = adminIdentity.key.secret

    await storage.init()
    await storage.setItem(token_object.prefix, { salt: token_object.salt, hash: token_object.hash, eth_priv_key: wallet.privateKey, iota_id: adminIdentity, iota: { credentials: {} } })
    console.log("Admin token " + token_object.token)
    await storage.setItem("admin", token_object.prefix)
  }
  else{
    console.log("Admin user already set.")
  }

}

async function check_admin(token){
  var split_token = token.split(".");
  const admin_prefix = await storage.getItem("admin")
  return admin_prefix == split_token[0]
}

async function check_exists(prefix){
  const user_object = await storage.getItem(prefix)
  return !(user_object == undefined)
}

module.exports = {
  generate_token,
  check_token,
  delete_token,
  get_acc_data,
  set_acc_data,
  set_admin,
  check_admin,
  check_exists
}