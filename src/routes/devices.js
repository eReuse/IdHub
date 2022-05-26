const express = require('express'),
router = express.Router();

const { BadRequest, NotFound, Forbidden } = require("../utils/errors")
const iota = require("../utils/iota/iota-helper.js")
const ethereum = require("../utils/ethereum/ethereum-config.js")
const ethHelper = require("../utils/ethereum/ethereum-helper.js")
const multiacc = require("../utils/multiacc-helper.js");


const ethereum_name = "ethereum"
const iota_name = "iota"
const cosmos_name = "cosmos"


iota.check_iota_index()

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

class Parameters {
  constructor(req) {
    this.api_token = req.body.api_token ?? "";
    this.deviceCHID = req.body.DeviceCHID ?? "";
    this.deviceDPP = req.body.DeviceDPP ?? "";
    this.documentID = req.body.DocumentID ?? "";
    this.documentSignature = req.body.DocumentSignature ?? "";
    this.issuerID = req.body.IssuerID ?? "";
    this.type = req.body.Type ?? "";
    this.dlt = req.headers.dlt ?? "";
    this.credentialType = req.body.CredentialType ?? "";
    //this.dlt = req.headers.dlt.replace(/\s+/g, '').split(',')
  }
}

function check_dlt(dlt) {
  // if (dlt.length != 1) {
  //   throw new BadRequest("Can only call one DLT at a time.")
  // }
  if (!dlt == iota_name && !dlt == ethereum_name) {
    throw new BadRequest("Invalid DLT identifier")
  }
}

function check_undefined_params(params) {
  if (params.includes(undefined) || params.includes("")) {
    throw new BadRequest("Invalid syntax.")
  }
}

router

.get('/', (req, res) => {
  res.send('EREUSE API')
})

.post("/registerDevice", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;
  try {
    console.log(`Called /registerDevice with chid: ${parameters.deviceCHID}`)

    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) != false)) {
        throw new BadRequest("Device already exists.")
      }
      var iota_creation_response = await iota.create_device_channel(iota_id, parameters.deviceCHID)
      
      var userData = await multiacc.get_acc_data(parameters.api_token)
      //it must be possible to do this better (maybe)
      if (userData.iota.credentials?.ownership == undefined){
        userData.iota.credentials.ownership = {[parameters.deviceCHID]: iota_creation_response.verifiableCredential}
      }
      else {
        userData.iota.credentials.ownership[parameters.deviceCHID] = iota_creation_response.verifiableCredential
      }
      await multiacc.set_acc_data(parameters.api_token, userData)

      response_data = {
        channelAddress: iota_creation_response.channelAddress,
        credential: iota_creation_response.verifiableCredential,
        timestamp: iota_creation_response.timestamp
      }
    }

    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)
      var existingDeviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (ethHelper.is_device_address_valid(existingDeviceAddress)) {
        throw new BadRequest("Device already exists.")
      }

      const deviceFactoryContract = ethHelper.createContract
      (ethereum.DEVICEFACTORY_ADDRESS, "../../../build/contracts/DeviceFactory.json", wallet)
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

.post("/deRegisterDevice", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /deRegisterDevice with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      //TODO: catch error if not found
      const credential = await iota.get_credential(parameters.api_token, parameters.credentialType, parameters.deviceCHID)
      var userData = await multiacc.get_acc_data(parameters.api_token)
      console.log("USER DATA " + userData)

      //empty payload?
      var iota_timestamp = await iota.write_device_channel(iota_id, credential, parameters.deviceCHID, "proof_of_deregister", {})

      response_data = {
        timestamp: iota_timestamp
      }
    }

    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)

      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
        (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

      var txResponse = await depositDeviceContract.deRegisterDevice(parameters.deviceCHID, { gasLimit: 6721975 })
      var txReceipt = await txResponse.wait()

      var args = ethHelper.getEvents
        (txReceipt, 'deRegisterProof', ethereum.depositDeviceIface)
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

.post("/issuePassport", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /issuePassport with DPP: ${parameters.deviceDPP}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceDPP, parameters.issuerID, parameters.documentID, parameters.documentSignature])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    var splitDeviceDPP = parameters.deviceDPP.split(":");
    const deviceCHID = splitDeviceDPP[0];
    const devicePHID = splitDeviceDPP[1];

    if (devicePHID == "" || splitDeviceDPP.length != 2) {
      throw new BadRequest("Incorrect DPP format.")
    }

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      //TODO: catch error if not found
      const credential = await iota.get_credential(parameters.api_token, parameters.credentialType, deviceCHID)

      var iota_timestamp = await iota.write_device_channel(iota_id, credential, deviceCHID, "proof_of_issue", {
        DeviceDPP: `${deviceCHID}:${devicePHID}`,
        IssuerID: parameters.issuerID,
        DocumentID: parameters.documentID,
        DocumentSignature: parameters.documentSignature
      })

      response_data = {
        timestamp: iota_timestamp
      }
    }

    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(deviceCHID)

      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

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

.post("/generateProof", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /generateProof with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID, parameters.issuerID, parameters.documentID, parameters.documentSignature, parameters.type])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      //TODO: catch error if not found
      const credential = await iota.get_credential(parameters.api_token, parameters.credentialType, parameters.deviceCHID)

      var iota_timestamp = await iota.write_device_channel(iota_id, credential, parameters.deviceCHID, "generic_proof", {
        IssuerID: parameters.issuerID,
        DocumentID: parameters.documentID,
        DocumentSignature: parameters.documentSignature,
        DocumentType: parameters.type
      })

      response_data = {
        timestamp: iota_timestamp
      }
    }

    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

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

.post("/getProofs", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /getProofs with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      //TODO: catch error if not found
      const credential = await iota.get_credential(parameters.api_token, parameters.credentialType, parameters.deviceCHID)

      var iota_proofs = await iota.read_specific_device_proofs(iota_id, credential, parameters.deviceCHID, "generic_proof")

      response_data = iota_proofs
    }

    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

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

.post("/getIssueProofs", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /getIssueProofs with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      //TODO: catch error if not found
      const credential = await iota.get_credential(parameters.api_token, parameters.credentialType, parameters.deviceCHID)

      var iota_proofs = await iota.read_specific_device_proofs(iota_id, credential, parameters.deviceCHID, "proof_of_issue")
      response_data = iota_proofs
    }


    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

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

.post("/getRegisterProofsByCHID", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /getRegisterProofsByCHID with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      //TODO: catch error if not found
      const credential = await iota.get_credential(parameters.api_token, parameters.credentialType, parameters.deviceCHID)

      var iota_proofs = await iota.read_specific_device_proofs(iota_id, credential, parameters.deviceCHID, "proof_of_register")

      response_data = iota_proofs
    }

    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

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

.post("/getDeRegisterProofs", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /getDeRegisterProofs with chid: ${parameters.deviceCHID}`)
    check_dlt(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      //TODO: catch error if not found
      const credential = await iota.get_credential(parameters.api_token, parameters.credentialType, parameters.deviceCHID)

      var iota_proofs = await iota.read_specific_device_proofs(iota_id, credential, parameters.deviceCHID, "proof_of_deregister")

      response_data = iota_proofs
    }

    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
        (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

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

// const port = 3010
// const host = "0.0.0.0"

// app.listen(port, host, () => {
//   console.log(`Example app listening at http://${host}:${port}`)
// })

module.exports = router
