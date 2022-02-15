const express = require('express')
const ethers = require("ethers")
const { BadRequest, NotFound ,Forbidden} = require("../utils/errors")
var bodyParser = require('body-parser')
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
const deviceFactoryContract = new ethers.Contract(
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
  var response =  await deviceFactoryContract.getAddressFromChid(chid)
  return response
}

function is_device_address_valid(deviceAddress){
  return !(deviceAddress == "0x0000000000000000000000000000000000000000")
                           //0x0000000000000000000000000000000000000000
}

function createContract(deviceAddress, contractPath){
  const depositDeviceContract = new ethers.Contract(
    deviceAddress,
    require(contractPath).abi,
    signer
  )
  return depositDeviceContract
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

app.post("/registerDevice", async (req, res, next) => {

  const chid = req.body.DeviceCHID;
  try{
    console.log(`Called /registerDevice with chid: ${chid}`)

    var existingDeviceAddress = await chid_to_deviceAdress(chid)
    if (is_device_address_valid(existingDeviceAddress)){
      res.status(406);
      res.json({
        status: "Device already exists.",
      })
      throw new BadRequest("Device already exists.")
    }

    var n = nonce++
    printNonce(n)
    var txResponse = await deviceFactoryContract.registerDevice(chid, {gasLimit:6721975,nonce:n})
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
    if (e.message != "Device already exists.") {
      res.status(500);
      res.json({
        status: "Blockchain service error.",
      })
    }
    next(e)
  }
})

app.post("/deRegisterDevice", async (req, res, next) => {

  const chid = req.body.DeviceCHID;

  try{
    console.log(`Called /deRegisterDevice with chid: ${chid}`)

    var deviceAddress = await chid_to_deviceAdress(chid)

    if (!is_device_address_valid(deviceAddress)) {
      res.status(406);
      res.json({
      status: "CHID not registered.",
    })
    throw new BadRequest("CHID not registered.")
    }
    
    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json")

    var n = nonce++
    printNonce(n)
    var txResponse = await depositDeviceContract.deRegisterDevice(chid, {gasLimit:6721975,nonce:n})
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
    if (e.message != "CHID not registered.") {
      res.status(500);
      res.json({
        status: "Blockchain service error.",
      })
    }
    next(e)
  }
})

app.post("/issuePassport", async (req, res, next) => {
  const deviceDPP = req.body.DeviceDPP;
  const documentID = req.body.DocumentID ?? "";
  const documentSignature = req.body.DocumentSignature ?? "";
  const issuerID = req.body.IssuerID ?? "";
  
  try{
    console.log(`Called /issuePassport with DPP: ${deviceDPP}`)

    var splitDeviceDPP = deviceDPP.split(":");
    const deviceCHID = splitDeviceDPP[0];
    const devicePHID = splitDeviceDPP[1];

    if (devicePHID == undefined)  {
      res.status(406);
      res.json({
        status: "Incorrect DPP format.",
      })
      throw new BadRequest("Incorrect DPP format.")
    }

    var deviceAddress = await chid_to_deviceAdress(deviceCHID)

    if (!is_device_address_valid(deviceAddress)) {
      res.status(406);
      res.json({
        status: "CHID not registered.",
      })
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json")

    n = nonce++

    printNonce(n)

    const txResponse = await depositDeviceContract.issuePassport(deviceCHID, devicePHID, documentID, documentSignature, issuerID, {gasLimit:6721975,nonce:n})
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
    if (e.message != "CHID not registered." && e.message != "Incorrect DPP format.") {
      res.status(500);
      res.json({
        status: "Blockchain service error.",
      })
    }
    next(e)
  }
})

app.post("/generateProof", async (req, res, next) => {
  const deviceCHID = req.body.DeviceCHID;
  const issuerID = req.body.IssuerID ?? "";
  const documentID = req.body.DocumentID ?? "";
  const documentSignature = req.body.DocumentSignature ?? "";
  const documentType = req.body.Type ?? "";

  try{
    console.log(`Called /generateProof with chid: ${deviceCHID}`)

    var deviceAddress = await chid_to_deviceAdress(deviceCHID)
    if (!is_device_address_valid(deviceAddress)) {
      res.status(406);
      res.json({
        status: "CHID not registered.",
      })
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json")

    n = nonce++
    printNonce(n)

    const txResponse = await depositDeviceContract.generateGenericProof(deviceCHID, issuerID, documentID, documentSignature, documentType, {gasLimit:6721975,nonce:n})
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
    if (e.message != "CHID not registered.") {
      res.status(500);
      res.json({
        status: "Blockchain service error.",
      })
    }
    next(e)
  }
})

app.post("/getProofs", async (req, res, next) => {
  const chid = req.body.DeviceCHID;
  try{
    console.log(`Called /getProofs with chid: ${chid}`)

    var deviceAddress = await chid_to_deviceAdress(chid)
    if (!is_device_address_valid(deviceAddress)) {
      res.status(406);
      res.json({
        status: "CHID not registered.",
      })
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json")

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
    if (e.message != "CHID not registered.") {
      res.status(500);
      res.json({
        status: "Blockchain service error.",
      })
    }
    next(e)
  }
})

app.post("/getIssueProofs", async (req, res, next) => {
  const chid = req.body.DeviceCHID;

  try{
    console.log(`Called /getIssueProofs with chid: ${chid}`)

    var deviceAddress = await chid_to_deviceAdress(chid)
    if (!is_device_address_valid(deviceAddress)) {
      res.status(406);
      res.json({
        status: "CHID not registered.",
      })
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json")

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
    if (e.message != "CHID not registered.") {
      res.status(500);
      res.json({
        status: "Blockchain service error.",
      })
    }
    next(e)
  }
})

app.post("/getRegisterProofsByCHID", async (req, res, next) => {
  const chid = req.body.DeviceCHID;
  try{
    console.log(`Called /getRegisterProofsByCHID with chid: ${chid}`)

    var deviceAddress = await chid_to_deviceAdress(chid)
    if (!is_device_address_valid(deviceAddress)) {
      res.status(406);
      res.json({
        status: "CHID not registered.",
      })
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = new ethers.Contract(
      deviceAddress,
      require('../../build/contracts/DepositDevice.json').abi,
      signer
    )

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
    if (e.message != "CHID not registered.") {
      res.status(500);
      res.json({
        status: "Blockchain service error.",
      })
    }
    next(e)
  }
})


app.post("/getDeRegisterProofs", async (req, res, next) => {
  const chid = req.body.DeviceCHID;
  try{
    console.log(`Called /getDeRegisterProofs with chid: ${chid}`)

    var deviceAddress = await chid_to_deviceAdress(chid)
    if (!is_device_address_valid(deviceAddress)) {
      res.status(406);
      res.json({
        status: "CHID not registered.",
      })
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = createContract(deviceAddress,"../../build/contracts/DepositDevice.json")

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
    if (e.message != "CHID not registered.") {
      res.status(500);
      res.json({
        status: "Blockchain service error.",
      })
    }
    next(e)
  }
})

app.listen(port, host, () => {
  console.log(`Example app listening at http://${host}:${port}`)
})

module.exports = app
