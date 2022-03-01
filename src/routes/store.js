const storage = require('node-persist');
const generate = require('generate-api-key');
const CryptoJS = require('crypto-js');
const ethers = require("ethers")

const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"



async function generate_token(){
    await storage.init();
    await storage.clear()
    var wallet
    const prefix = generate({length: 15, pool: characters})
    const token = generate({length: 64, pool: characters, prefix: prefix})
    const salt = generate({length: 64, pool: characters})

    wallet = ethers.Wallet.createRandom()
    var split_token = token.split(".");

    const hash = CryptoJS.SHA3(split_token[1]+salt, { outputLength: 256 }).toString(CryptoJS.enc.Hex);

    await storage.setItem(prefix,{salt:salt, hash:hash, eth_key: wallet.privateKey})
    

    console.log(`${prefix}\n${token}\n${salt}\n${hash}`)
}

async function check_token(token){
    await storage.init();
    var split_token = token.split(".");
    const item = await storage.getItem(split_token[0]);

    if(item == undefined) return false

    const hash = CryptoJS.SHA3(split_token[1]+item.salt, { outputLength: 256 }).toString(CryptoJS.enc.Hex)
    console.log(hash == item.hash)
    console.log(split_token[2])
}

generate_token()
//check_token("9Y44aRjdkbJrMf.bQesUQzKzsqfZppeLWJ0BClWjKcVmZu7A5ocZDWqKKPzfgpVeZccjgu5IPexhm3W")