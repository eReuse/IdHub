const CryptoJS = require('crypto-js');
const storage = require('node-persist');
// const generate = require('generate-api-key');
const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
const ethers = require("ethers")
const ethereum = require("../utils/ethereum/ethereum-config.js");
const { setMask } = require('readline-sync');

const fs = require("fs")
const SHARED = process.env.SHARED

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

  const admin_object = await storage.getItem("admin")
  if (admin_object == undefined) {
    console.log("Setting admin user...")
    const privateKey = "0x807118c237e01677f0522f9ca50535b1984481ea2e09115197934a9cd73ab8c1"
    const token_object = generate_token()
    const wallet = new ethers.Wallet(privateKey, ethereum.provider)

    await storage.init()
    await storage.setItem(token_object.prefix, { salt: token_object.salt, hash: token_object.hash, eth_priv_key: wallet.privateKey})
    console.log("Admin token " + token_object.token)
    if(SHARED) {
	    const admin_token_file = SHARED + "/api-connector_admin-token.txt"
	    fs.writeFileSync(admin_token_file, token_object.token)
    }
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
