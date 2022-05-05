const express = require('express')
const ethers = require("ethers")
const { BadRequest, NotFound, Forbidden } = require("../utils/errors")
var bodyParser = require('body-parser')
const storage = require('node-persist');
const iota = require("./iota-helper")
const ethereum = require("./ethereum-config.js")
const ethHelper = require("./ethereum-helper.js")
const multiacc = require("./multiacc-helper.js")

const ethereum_name = "ethereum"
const iota_name = "iota"
const cosmos_name = "cosmos"


iota.check_iota_index()

const app = express()
app.use(bodyParser.json())
app.use(
  bodyParser.urlencoded({
    extended: true,
  })
)

var nonce

ethereum.signer.getTransactionCount().then(n => {
  nonce = n
})

app.get('/', (req, res) => {
  res.send('EREUSE API')
})

function printNonce(n) {
  console.log(`Nonce: ${n}`)
}

function get_error_object(error) {
  switch (error) {
    case "Device already exists.":
      return { code: 406, message: error }
    case "CHID not registered.":
      return { code: 406, message: error }
    case "Incorrect DPP format.":
      return { code: 406, message: error }
    case "Couldn't register the user.":
      return { code: 500, message: error }
    case "Invalid API token.":
      return { code: 500, message: error }
    case "Couldn't invalidate the user.":
      return { code: 500, message: error }
  }
  return { code: 500, message: "Blockchain service error." }
}

app.post("/registerUser", async (req, res, next) => {
  const privateKey = req.body.privateKey ?? ""
  var wallet
  try {
    console.log(`Called /registerUser`)
    const token_object = multiacc.generate_token()
    if (privateKey == "") {
      wallet = ethers.Wallet.createRandom()
    }
    else {
      wallet = new ethers.Wallet(privateKey, ethereum.provider)
    }

    //Creation of IOTA identity.
    //TODO: check if it's provided in request.
    var iota_id = await iota.create_identity()

    await storage.setItem(token_object.prefix, { salt: token_object.salt, hash: token_object.hash, eth_priv_key: wallet.privateKey, iota_id: iota_id })
    res.json({
      status: "Success.",
      data: {
        api_token: token_object.token,
        eth_pub_key: wallet.address,
        eth_priv_key: wallet.privateKey,
        iota_id: iota_id
      }
    })
  }
  catch (e) {
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
  try {
    console.log(`Called /invalidateUser`)
    const deleted = await multiacc.delete_token(api_token)
    if (!deleted) throw new BadRequest("Invalid API token.")
    res.json({
      status: "Success.",
      data: {
        deleted_token: api_token
      }
    })
  }
  catch (e) {
    const error_object = get_error_object("Couldn't invalidate the user.")
    res.status(error_object.code);
    res.json({
      status: error_object.message,
    })
    next(e)
  }

})

class Parameters {
  constructor(req) {
    this.api_token = req.body.api_token ?? "";
    this.deviceCHID = req.body.DeviceCHID ?? "";
    this.deviceDPP = req.body.DeviceDPP ?? "";
    this.documentID = req.body.DocumentID ?? "";
    this.documentSignature = req.body.DocumentSignature ?? "";
    this.issuerID = req.body.IssuerID ?? "";
    this.type = req.body.Type ?? "";
    this.dlt = req.headers.dlt.replace(/\s+/g, '').split(',')
  }
}

function check_dlt(dlt) {
  if (dlt.length != 1) {
    throw new BadRequest("Can only call one DLT at a time.")
  }
  else if (!dlt.includes("iota") && !dlt.includes("ethereum")) {
    throw new BadRequest("Invalid DLT identifier")
  }
}

function check_undefined_params(params) {
  if (params.includes(undefined) || params.includes("")) {
    throw new BadRequest("Invalid syntax.")
  }
}

app.post("/registerDevice", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;
  try {
    console.log(`Called /registerDevice with chid: ${parameters.deviceCHID}`)

    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt.includes(iota_name)) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) != false)) {
        throw new BadRequest("Device already exists.")
      }
      var iota_creation_response = await iota.create_device_channel(iota_id, parameters.deviceCHID)

      response_data = {
        channelAddress: iota_creation_response.retChannel,
        timestamp: iota_creation_response.timestamp
      }
    }

    else if (parameters.dlt.includes(ethereum_name)) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)
      var existingDeviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (ethHelper.is_device_address_valid(existingDeviceAddress)) {
        throw new BadRequest("Device already exists.")
      }

      const deviceFactoryContract = ethHelper.createContract
      (ethereum.DEVICEFACTORY_ADDRESS, "../../build/contracts/DeviceFactory.json", wallet)
      var txResponse = await deviceFactoryContract.registerDevice(parameters.deviceCHID, { gasLimit: 6721975 })
      var txReceipt = await txResponse.wait()
      var args = ethHelper.getEvents
      (txReceipt, 'DeviceRegistered', ethereum.deviceFactoryIface)

      response_data = {
        deviceAddress: args._deviceAddress,
        timestamp: parseInt(Number(args.timestamp), 10)
      }
    }

    res.status(201);
    res.json({
      data: response_data
    })
  }

  catch (e) {
    const error_object = get_error_object(e.message)
    res.status(error_object.code);
    res.json({
      error: error_object.message,
    })
    next(e)
  }
})

app.post("/deRegisterDevice", async (req, res, next) => {
  const parameters = new Parameters(req)

  try {
    console.log(`Called /deRegisterDevice with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await ethHelper.get_wallet(parameters.api_token)

    var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)

    if (!ethHelper.is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = ethHelper.createContract
    (deviceAddress, "../../build/contracts/DepositDevice.json", wallet)

    var txResponse = await depositDeviceContract.deRegisterDevice(parameters.deviceCHID, { gasLimit: 6721975 })
    var txReceipt = await txResponse.wait()

    var args = ethHelper.getEvents
    (txReceipt, 'deRegisterProof', ethereum.depositDeviceIface)

    res.status(201);
    res.json({
      data: {
        timestamp: parseInt(Number(args.timestamp), 10)
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
  const parameters = new Parameters(req)
  var response_data;
  var n_errors = 0

  try {
    console.log(`Called /issuePassport with DPP: ${parameters.deviceDPP}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceDPP, parameters.issuerID, parameters.documentID, parameters.documentSignature])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    var splitDeviceDPP = parameters.deviceDPP.split(":");
    const deviceCHID = splitDeviceDPP[0];
    const devicePHID = splitDeviceDPP[1];

    if (devicePHID == "" || splitDeviceDPP.length < 2) {
      throw new BadRequest("Incorrect DPP format.")
    }

    if (parameters.dlt.includes(iota_name)) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      var iota_timestamp = await iota.write_device_channel(iota_id, deviceCHID, "proof_of_issue", {
        DeviceDPP: `${deviceCHID}:${devicePHID}`,
        IssuerID: parameters.issuerID,
        DocumentID: parameters.documentID,
        DocumentSignature: parameters.documentSignature
      })

      response_data = {
        timestamp: iota_timestamp
      }
    }

    if (parameters.dlt.includes(ethereum_name)) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(deviceCHID)

      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../build/contracts/DepositDevice.json", wallet)

      const txResponse = await depositDeviceContract.issuePassport(deviceCHID, devicePHID, parameters.documentID, parameters.documentSignature, parameters.issuerID, { gasLimit: 6721975 })
      const txReceipt = await txResponse.wait()
      var args = ethHelper.getEvents
      (txReceipt, 'issueProof', ethereum.depositDeviceIface)

      response_data = {
        timestamp: parseInt(Number(args.timestamp), 10)
      }
    }

    res.status(201);
    res.json({
      data: response_data
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
  const parameters = new Parameters(req)
  var response_data;
  var n_errors = 0

  try {
    console.log(`Called /generateProof with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID, parameters.issuerID, parameters.documentID, parameters.documentSignature, parameters.type])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt.includes(iota_name)) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      var iota_timestamp = await iota.write_device_channel(iota_id, parameters.deviceCHID, "generic_proof", {
        IssuerID: parameters.issuerID,
        DocumentID: parameters.documentID,
        DocumentSignature: parameters.documentSignature,
        DocumentType: parameters.type
      })

      response_data = {
        timestamp: iota_timestamp
      }
    }

    if (parameters.dlt.includes(ethereum_name)) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../build/contracts/DepositDevice.json", wallet)

      const txResponse = await depositDeviceContract.generateGenericProof(parameters.deviceCHID, parameters.issuerID, parameters.documentID, parameters.documentSignature, parameters.type, { gasLimit: 6721975 })
      const txReceipt = await txResponse.wait()
      var args = ethHelper.getEvents
      (txReceipt, 'genericProof', ethereum.depositDeviceIface)

      response_data = {
        timestamp: parseInt(Number(args.timestamp), 10)
      }
    }

    res.status(201);
    res.json({
      data: response_data
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
  const parameters = new Parameters(req)
  var response_data;
  var n_errors = 0

  try {
    console.log(`Called /getProofs with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt.includes(iota_name)) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      var iota_proofs = await iota.read_device_generic_proofs(iota_id, parameters.deviceCHID)

      response_data = iota_proofs
    }

    if (parameters.dlt.includes(ethereum_name)) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../build/contracts/DepositDevice.json", wallet)

      const value = await depositDeviceContract.getGenericProofs();
      var data = []
      if (value.length != 0) {
        value.forEach(elem => {
          let proof_data = {
            IssuerID: elem[1],
            DocumentID: elem[2],
            DocumentSignature: elem[3],
            DocumentType: elem[4],
            timestamp: parseInt(Number(elem[5]), 10),
            blockNumber: parseInt(Number(elem[6]), 10),
          }
          data.push(proof_data)
        })
      }
      response_data = data
    }

    res.status(200);
    res.json({
      data: response_data,
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
  const parameters = new Parameters(req)
  var response_data;
  var n_errors = 0

  try {
    console.log(`Called /getIssueProofs with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt.includes(iota_name)) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      var iota_proofs = await iota.read_device_proofs_of_issue(iota_id, parameters.deviceCHID)
      response_data = iota_proofs
    }


    if (parameters.dlt.includes(ethereum_name)) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../build/contracts/DepositDevice.json", wallet)

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
      response_data = data
    }

    res.status(200);
    res.json({
      data: response_data,
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
  const parameters = new Parameters(req)
  var response_data;
  var n_errors = 0

  try {
    console.log(`Called /getRegisterProofsByCHID with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt.includes(iota_name)) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      var iota_proofs = await iota.read_device_proofs_of_register(iota_id, parameters.deviceCHID)

      response_data = iota_proofs
    }

    if (parameters.dlt.includes(ethereum_name)) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../build/contracts/DepositDevice.json", wallet)

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

      response_data = data
    }

    res.status(200);
    res.json({
      data: response_data,
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
  const parameters = new Parameters(req)

  try {
    console.log(`Called /getDeRegisterProofs with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")
    const wallet = await ethHelper.get_wallet(parameters.api_token)

    var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
    if (!ethHelper.is_device_address_valid(deviceAddress)) {
      throw new BadRequest("CHID not registered.")
    }

    const depositDeviceContract = ethHelper.createContract
    (deviceAddress, "../../build/contracts/DepositDevice.json", wallet)

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

    res.status(200);
    res.json({
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

app.listen(ethereum.port, ethereum.host, () => {
  console.log(`Example app listening at http://${ethereum.host}:${ethereum.port}`)
})

module.exports = app
