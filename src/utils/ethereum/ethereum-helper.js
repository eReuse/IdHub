const ethers = require("ethers")
const storage = require('node-persist');
const ethereum = require("./ethereum-config.js")
const axios = require('axios')

const CHAIN_ID = process.env.CHAIN_ID

async function chid_to_deviceAdress(chid) {
    var response = await ethereum.defaultDeviceFactoryContract.getAddressFromChid(chid)
    return response
}

function is_device_address_valid(deviceAddress) {
    return !(deviceAddress == "0x0000000000000000000000000000000000000000")
}

async function get_wallet(token) {
    var split_token = token.split(".");
    const item = await storage.getItem(split_token[0]);

    //skip check for undefined as this should only be called after checking the token validity
    const wallet = new ethers.Wallet(item.eth_priv_key, ethereum.provider)
    return wallet
}

function randomWallet(){
    var wallet = ethers.Wallet.createRandom()
    wallet = wallet.connect(ethereum.provider)
    return wallet
}

function createContract(address, contractJSON, wallet) {
    const contract = new ethers.Contract(
        address,
        contractJSON.abi,
        wallet
    )
    return contract
}

function getEvents(txReceipt, event, interface) {
    var args;
    txReceipt.logs.forEach(log => {
        if (log.eventName != undefined && log.eventName == event) {
            args = interface.parseLog(log).args
        }
    })
    return args;
}

function translateHexToString(n, string) {
    var translation = ethers.utils.toUtf8String('0x' + string.substring(n));
    return translation
}

async function makeReceiptCall(hash) {
    var data = JSON.stringify({
        "jsonrpc": "2.0",
        "method": "eth_getTransactionReceipt",
        "params": [
            hash
        ],
        "id": CHAIN_ID
    });
    var config = {
        method: 'POST',
        url: ethereum.nodeIP,
        headers: {
            'Content-Type': 'application/json'
        },
        data: data
    };
    return result = await axios(config)
}



module.exports = {
    chid_to_deviceAdress,
    is_device_address_valid,
    get_wallet,
    createContract,
    getEvents,
    translateHexToString,
    randomWallet,
    makeReceiptCall
}
