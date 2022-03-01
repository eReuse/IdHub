const express = require('express')
const ethers = require("ethers")
const { BadRequest, NotFound ,Forbidden} = require("../utils/errors")
var bodyParser = require('body-parser')
const storage = require('node-persist');
const generate = require('generate-api-key');
const CryptoJS = require('crypto-js');

storage.init();

const characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

const app = express()
app.use(bodyParser.json())
app.use(
  bodyParser.urlencoded({
    extended: true,
  })
)
const port = 3005
const host = "0.0.0.0"

const DeviceFactory = require('../../build/contracts/DeviceFactory.json');
//457
const DEVICEFACTORY_ADDRESS = DeviceFactory.networks['457'].address;

//const privateKey = "0c59d9a51420d950c5bf1ee3e52114f2be893680e432a95038b179e3b6e9d0e6"
const privateKey = "92ef10a0fdac0901d81e46fa42f6444645b0fb252cca8ae2a585f3fb2686fa2d"

const deviceFactoryIface = new ethers.utils.Interface(
  require('../../build/contracts/DeviceFactory.json').abi
)
const depositDeviceIface = new ethers.utils.Interface(
  require('../../build/contracts/DepositDevice.json').abi
)

const provider = new ethers.providers.JsonRpcProvider(
  "HTTP://10.1.3.30:8545"
  //"HTTP://127.0.0.1:7545"
)


const signer = new ethers.Wallet(privateKey, provider)
const defaultDeviceFactoryContract = new ethers.Contract(
  DEVICEFACTORY_ADDRESS,
  require('../../build/contracts/DeviceFactory.json').abi,
  signer
)
var nonce

signer.getTransactionCount().then(n => {
  nonce = n
})

app.get('/', (req, res) => {
  res.send('BESU API')
})

async function chid_to_deviceAdress(chid){
  var response =  await defaultDeviceFactoryContract.getAddressFromChid(chid)
  return response
}

function is_device_address_valid(deviceAddress){
  return !(deviceAddress == "0x0000000000000000000000000000000000000000")
                           //0x0000000000000000000000000000000000000000
}

function generate_token() {
  const prefix = generate({ length: 15, pool: characters })
  const token = generate({ length: 64, pool: characters, prefix: prefix })
  const salt = generate({ length: 64, pool: characters })

  var split_token = token.split(".");

  const hash = CryptoJS.SHA3(split_token[1] + salt, { outputLength: 256 }).toString(CryptoJS.enc.Hex);

  return {prefix:prefix, token:token, salt: salt, hash: hash }
}

async function check_token(token) {
  if (token == undefined) return false
  var split_token = token.split(".");
  const item = await storage.getItem(split_token[0]);

  if(item == undefined) return false

  const hash = CryptoJS.SHA3(split_token[1] + item.salt, { outputLength: 256 }).toString(CryptoJS.enc.Hex)
  return hash == item.hash
}

async function delete_token(token){
  const valid_token = await check_token(token)
  if(!valid_token) return false
  var split_token = token.split(".");
  const result = await storage.removeItem(split_token[0])

  return result.removed
  
}

async function get_wallet(token) {
  var split_token = token.split(".");
  const item = await storage.getItem(split_token[0]);

  //skip check for undefined as this should only be called after checking the token validity
  const wallet = new ethers.Wallet(item.eth_priv_key, provider)
  return wallet
}

function createContract(address, contractPath, wallet){
  const contract = new ethers.Contract(
    address,
    require(contractPath).abi,
    wallet
  )
  return contract
}

function getEvents(txReceipt, event, interface) {
  var args;
  txReceipt.events.forEach(log => {
    if (log.event == event){
      args = interface.parseLog(log).args
    }
  })
  return args;
}

function printNonce(n){
  console.log(`Nonce: ${n}`)
}

function get_error_object(error){
  switch (error){
    case "Device already exists.":
      return {code:406, message:error}
    case "CHID not registered.":
      return {code:406, message:error}
    case "Incorrect DPP format.":
      return {code:406, message:error}
    case "Couldn't register the user.":
      return {code:500, message:error}
    case "Invalid API token.":
      return {code:500, message:error}
    case "Couldn't invalidate the user.":
      return {code:500, message:error}
  }
  return {code:500, message:"Blockchain service error."}
}

app.post("/registerUser", async (req, res, next) => {
  const privateKey = req.body.privateKey ?? ""
  var wallet
  try{
    console.log(`Called /registerUser`)
    const token_object = generate_token()
    if (privateKey == "") {
      wallet = ethers.Wallet.createRandom()
    }
    else{
      wallet = new ethers.Wallet(privateKey, provider)
    }
    await storage.setItem(token_object.prefix, {salt: token_object.salt, hash: token_object.hash, eth_priv_key: wallet.privateKey})
    res.json({
      status: "Success.",
      data: {
        api_token: token_object.token,
        eth_pub_key: wallet.address,
        eth_priv_key: wallet.privateKey
      }
    })
  }
  catch (e){
    const error_object = get_error_object("Couldn't register the user.")
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }

})


app.post("/invalidateUser", async (req, res, next) => {
  const api_token = req.body.api_token;
  try{
    console.log(`Called /invalidateUser`)
    const deleted = await delete_token(api_token)
    if (!deleted) throw new BadRequest("Invalid API token.")
    res.json({
      status: "Success.",
      data: {
        deleted_token: api_token
      }
    })
  }
  catch (e){
    const error_object = get_error_object("Couldn't invalidate the user.")
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }

})



app.post("/registerDevice", async (req, res, next) => {

  const chid = req.body.DeviceCHID ?? "";
  const api_token = req.body.api_token;
  try{
    console.log(`Called /registerDevice with chid: ${chid}`)

    const valid_token = await check_token(api_token)
    if(!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await get_wallet(api_token)

    var existingDeviceAddress = await chid_to_deviceAdress(chid)
    if (is_device_address_valid(existingDeviceAddress) || chid == ""){
      throw new BadRequest("Device already exists.")
    }

    const deviceFactoryContract = createContract(DEVICEFACTORY_ADDRESS,"../../build/contracts/DeviceFactory.json",wallet)

    var txResponse = await deviceFactoryContract.registerDevice(chid, {gasLimit:6721975})
    var txReceipt = await txResponse.wait()
    var args = getEvents(txReceipt, 'DeviceRegistered',deviceFactoryIface)

    res.status(201);
    res.json({
      status: "Success",
      data: {
        deviceAddress: args._deviceAddress,
        timestamp: parseInt(Number(args.timestamp),10)
      },
    })
  }
  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }
})

app.post("/deRegisterDevice", async (req, res, next) => {

  const chid = req.body.DeviceCHID ?? "";
  const api_token = req.body.api_token;

  try{
    console.log(`Called /deRegisterDevice with chid: ${chid}`)

    const valid_token = await check_token(api_token)
    if(!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await get_wallet(api_token)

    var deviceAddress = await chid_to_deviceAdress(chid)

    if (!is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }
    
    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json", wallet)

    var txResponse = await depositDeviceContract.deRegisterDevice(chid, {gasLimit:6721975})
    var txReceipt = await txResponse.wait()

    var args = getEvents(txReceipt, 'deRegisterProof',depositDeviceIface)

    res.status(201);
    res.json({
      status: "Success",
      data: {
        timestamp: parseInt(Number(args.timestamp),10)
      },
    })
  }
  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }
})

app.post("/issuePassport", async (req, res, next) => {
  const deviceDPP = req.body.DeviceDPP ?? "";
  const documentID = req.body.DocumentID ?? "";
  const documentSignature = req.body.DocumentSignature ?? "";
  const issuerID = req.body.IssuerID ?? "";
  const api_token = req.body.api_token;
  
  try{
    console.log(`Called /issuePassport with DPP: ${deviceDPP}`)

    const valid_token = await check_token(api_token)
    if(!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await get_wallet(api_token)

    var splitDeviceDPP = deviceDPP.split(":");
    const deviceCHID = splitDeviceDPP[0];
    const devicePHID = splitDeviceDPP[1];

    if (devicePHID == "" || splitDeviceDPP.length <2)  {
      throw new BadRequest("Incorrect DPP format.")
    }

    var deviceAddress = await chid_to_deviceAdress(deviceCHID)

    if (!is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json", wallet)

    const txResponse = await depositDeviceContract.issuePassport(deviceCHID, devicePHID, documentID, documentSignature, issuerID, {gasLimit:6721975})
    const txReceipt = await txResponse.wait()
    var args = getEvents(txReceipt, 'issueProof',depositDeviceIface)
    res.status(201);
    res.json({
      status: "Success",
      data: {
        timestamp: parseInt(Number(args.timestamp),10)
      },
    })

  }
  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }
})

app.post("/generateProof", async (req, res, next) => {
  const deviceCHID = req.body.DeviceCHID ?? "";
  const issuerID = req.body.IssuerID ?? "";
  const documentID = req.body.DocumentID ?? "";
  const documentSignature = req.body.DocumentSignature ?? "";
  const documentType = req.body.Type ?? "";
  const api_token = req.body.api_token;

  try{
    console.log(`Called /generateProof with chid: ${deviceCHID}`)

    const valid_token = await check_token(api_token)
    if(!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await get_wallet(api_token)

    var deviceAddress = await chid_to_deviceAdress(deviceCHID)
    if (!is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json", wallet)

    const txResponse = await depositDeviceContract.generateGenericProof(deviceCHID, issuerID, documentID, documentSignature, documentType, {gasLimit:6721975})
    const txReceipt = await txResponse.wait()
    var args = getEvents(txReceipt, 'genericProof',depositDeviceIface)
    res.status(201);
    res.json({
      status: "Success",
      data: {
        timestamp: parseInt(Number(args.timestamp),10)
      },
    })

  }
  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }
})

app.post("/getProofs", async (req, res, next) => {
  const chid = req.body.DeviceCHID ?? "";
  const api_token = req.body.api_token;
  try{
    console.log(`Called /getProofs with chid: ${chid}`)

    const valid_token = await check_token(api_token)
    if(!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await get_wallet(api_token)

    var deviceAddress = await chid_to_deviceAdress(chid)
    if (!is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json",wallet)

    const value = await depositDeviceContract.getGenericProofs();
    var data = []
    if (value.length != 0) {
      value.forEach(elem => {
        let proof_data = {
          IssuerID: elem[1],
          DocumentID: elem[2],
          DocumentSignature: elem[3],
          DocumentType: elem[4],
          timestamp: parseInt(Number(elem[5]),10),
          blockNumber: parseInt(Number(elem[6]),10),
        }
        data.push(proof_data)
      })
    }

    res.json({
      status: "Success",
      data: data,
    })
  }
  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }
})

app.post("/getIssueProofs", async (req, res, next) => {
  const chid = req.body.DeviceCHID ?? "";
  const api_token = req.body.api_token;

  try{
    console.log(`Called /getIssueProofs with chid: ${chid}`)

    const valid_token = await check_token(api_token)
    if(!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await get_wallet(api_token)

    var deviceAddress = await chid_to_deviceAdress(chid)
    if (!is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json", wallet)

    const value = await depositDeviceContract.getIssueProofs();
    var data = []
    if (value.length != 0) {
      value.forEach(elem => {
        let proof_data = {
          DeviceDPP: `${elem[0]}:${elem[1]}`,
          IssuerID: elem[4],
          DocumentID: elem[2],
          DocumentSignature: elem[3],
          timestamp: parseInt(Number(elem[5]), 10),
          blockNumber: parseInt(Number(elem[6]), 10),
        }
        data.push(proof_data)
      })
    }
    res.json({
      status: "Success",
      data: data,
    })
  }
  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }
})

app.post("/getRegisterProofsByCHID", async (req, res, next) => {
  const chid = req.body.DeviceCHID ?? "";
  const api_token = req.body.api_token;
  try{
    console.log(`Called /getRegisterProofsByCHID with chid: ${chid}`)

    const valid_token = await check_token(api_token)
    if(!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await get_wallet(api_token)

    var deviceAddress = await chid_to_deviceAdress(chid)
    if (!is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json", wallet)

    const value = await depositDeviceContract.getRegisterProofs();
    var data = []
    if (value.length != 0) {
      value.forEach(elem => {
        let proof_data = {
          //DeviceCHID: elem[0], //FIX
          timestamp: parseInt(Number(elem[1]), 10),
          blockNumber: parseInt(Number(elem[2]), 10),
        }
        data.push(proof_data)
      })
    }

    res.json({
      status: "Success",
      data: data,
    })
  }
  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }
})


app.post("/getDeRegisterProofs", async (req, res, next) => {
  const chid = req.body.DeviceCHID ?? "";
  const api_token = req.body.api_token;
  try{
    console.log(`Called /getDeRegisterProofs with chid: ${chid}`)

    const valid_token = await check_token(api_token)
    if(!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await get_wallet(api_token)

    var deviceAddress = await chid_to_deviceAdress(chid)
    if (!is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json", wallet)

    const value = await depositDeviceContract.getDeRegisterProofs();
    var data = []
    if (value.length != 0) {
      value.forEach(elem => {
        let proof_data = {
          DeviceCHID: elem[0],
          timestamp: parseInt(Number(elem[1]), 10),
          blockNumber: parseInt(Number(elem[2]), 10),
        }
        data.push(proof_data)
      })
    }

    res.json({
      status: "Success",
      data: data,
    })
  }
  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }
})

app.listen(port, host, () => {
  console.log(`Example app listening at http://${host}:${port}`)
})

module.exports = app
