const express = require("express")
var bodyParser = require('body-parser')
const apiErrorHandler = require('./utils/apiErrorHandler')
const endpoints = require('./endpoints.js')

const fs = require('fs');
const path = require('path');

const ethers = require("ethers")
const axios = require("axios")
const dotenv = require('dotenv');
dotenv.config();

const nodeIP = process.env.NODE_IP
const idIndexUrl = process.env.ID_INDEX

const provider = new ethers.providers.JsonRpcProvider(
    nodeIP
)

const depositDeviceIface = new ethers.utils.Interface(
    require('../shared/DepositDevice.json').abi
)

const dataDir = '../data';
const filePath = path.join(dataDir, 'devices.json');


async function process_event(parsed_log) {
    try {
        let inventoryUrl = idIndexUrl + "/getURL?id=" + parsed_log.args.inventoryID
        console.log(inventoryUrl)
        let response = await axios.get(inventoryUrl)
        let deviceData = await axios.get(`${response.data.url + "/did/" + parsed_log.args.chid + ":" + parsed_log.args.phid}`)
        let fileData = fs.readFileSync(filePath, 'utf8');
        let jsonData = JSON.parse(fileData);
        let device = JSON.parse(deviceData.data.data.document).device
        device.chid = parsed_log.args.chid
        device.phid = parsed_log.args.phid
        jsonData.push(device)
        fs.writeFileSync(filePath, JSON.stringify(jsonData));
    } catch (err) {
        console.log("Something went wrong when fetching a device." + err)
    }
}

filter = {
    address: null,
    topics: [
        ethers.utils.id("genericProof(address,string,string,address,string,string,string,uint256,string)")
        // "0x20cb444c6cae9492d946d50520d539be4dc7b6718a10460e135a430f1f379285"
    ]
    // topics: null
}
provider.on(filter, (log, event) => {
    let parsed_log = depositDeviceIface.parseLog(log)
    if (parsed_log.args.documentType == "DPP_creation"){
        setTimeout(()=>process_event(parsed_log), 20000)
        console.log("Task scheduled: "+ parsed_log.args.chid)
    }
    // if (parsed_log.args.documentType == "Device_creation") {
    //     try {
    //         let inventoryUrl = idIndexUrl + "/getURL?id=" + parsed_log.args.inventoryID
    //         console.log(inventoryUrl)
    //         axios.get(inventoryUrl)
    //             .then(response => {
    //                 try {
    //                     axios.get(`${response.data.url + "/did/" + parsed_log.args.chid}`)
    //                         .then(deviceData => {
    //                             try {
    //                                 let fileData = fs.readFileSync(filePath, 'utf8');
    //                                 let jsonData = JSON.parse(fileData);
    //                                 let device = JSON.parse(deviceData.data.data[0].document).device
    //                                 device.chid = parsed_log.args.chid
    //                                 jsonData.push(device)
    //                                 fs.writeFileSync(filePath, JSON.stringify(jsonData));
    //                             } catch (err) {
    //                                 console.log("Something went wrong when fetching a device. 2" + err)
    //                             }
    //                         })
    //                 } catch (err) {
    //                     console.log("Something went wrong when fetching a device. 1" + err)
    //                 }
    //             })
    //     } catch (err) {
    //         console.log("Something went wrong when fetching a device." + err)
    //     }
    // }
})

const app = express()
app.use(bodyParser.json())
app.use(
    bodyParser.urlencoded({
        extended: true,
    })
)

const port = 3013
const host = "0.0.0.0"



function checkOrCreateJSONFile() {

  try {
    // Check if the data directory exists
    fs.accessSync(dataDir);

    // Data directory exists, check if file exists
    fs.accessSync(filePath);

    // File exists, do nothing
    console.log('devices.json exists.');
  } catch (error) {
    // File or data directory doesn't exist, create them
    console.log('File or data directory does not exist. Creating...');

    const defaultJson = [];

    // Create the data directory if it doesn't exist
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir);
    }

    fs.writeFileSync(filePath, JSON.stringify(defaultJson));
    console.log('File created with default value:', defaultJson);
  }
}

checkOrCreateJSONFile();

app.use("/", endpoints)

app.use(apiErrorHandler);

app.listen(port, host, () => {
    console.log(`Example app listening at http://${host}:${port}`)
})