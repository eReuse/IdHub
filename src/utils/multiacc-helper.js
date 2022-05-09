const CryptoJS = require('crypto-js');
const storage = require('node-persist');
const generate = require('generate-api-key');

const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


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

module.exports = {
  generate_token,
  check_token,
  delete_token,
}