const express = require('express'),
router = express.Router();

//const { BadRequest, NotFound, Forbidden } = require("../utils/errors")
const ApiError = require('../utils/apiError')

const iota = require("../utils/iota/iota-helper.js")
const ethereum = require("../utils/ethereum/ethereum-config.js")
const ethHelper = require("../utils/ethereum/ethereum-helper.js")
const multiacc = require("../utils/multiacc-helper.js");

const {OPERATOR, WITNESS, VERIFIER, OWNERSHIP} = require('../utils/constants')


const ethereum_name = "ethereum"
const iota_name = "iota"
const cosmos_name = "cosmos"


// async function initial_steps(){
//   await iota.check_iota_index()
//   await multiacc.set_admin()
// }
//initial_steps()

async function temp_error(tx){
try {
          let code = await ethereum.provider.call(tx, tx.blockNumber)
        } catch (er){
          try{
            reason = er.error.error.message
            return reason.slice(20)
          } catch(err){
            return "THIS SHOULDN'T HAPPEN"
          }
        }
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
    this.newOwner = req.body.NewOwner ?? "";
    this.endpoint = req.body.endpoint ?? "";
    this.description = req.body.description ?? "";
    this.fragment = req.body.fragment ?? "";
    //this.dlt = req.headers.dlt.replace(/\s+/g, '').split(',')
  }
}

function is_dlt_valid(dlt) {
  if (dlt == iota_name || dlt == ethereum_name) {
    return true
  }
  return false
}

function check_undefined_params(params) {
  if (params.includes(undefined) || params.includes("")) {
    return true;
  }
  return false;
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

    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    if (check_undefined_params([parameters.deviceCHID])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) != false)) {
        next(ApiError.badRequest('Device already exists'));
        return
      }
      const credential = await iota.get_credential(parameters.api_token, [OPERATOR, WITNESS])
      if(credential == undefined) {
        next(ApiError.badRequest('No valid credential found'));
        return
      }
      var iota_creation_response = await iota.create_device_channel(iota_id, parameters.deviceCHID)
      
      var userData = await multiacc.get_acc_data(parameters.api_token)
      //it must be possible to do this better (maybe)
      if (userData.iota.credentials?.[OWNERSHIP] == undefined){
        userData.iota.credentials[OWNERSHIP] = {[parameters.deviceCHID]: iota_creation_response.verifiableCredential}
      }
      else {
        userData.iota.credentials[OWNERSHIP][parameters.deviceCHID] = iota_creation_response.verifiableCredential
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
        next(ApiError.badRequest('Device already exists'));
        return
      }

      const deviceFactoryContract = ethHelper.createContract
      (ethereum.DEVICEFACTORY_ADDRESS, "../../../build/contracts/DeviceFactory.json", wallet)
      var txResponse = await deviceFactoryContract.registerDevice(parameters.deviceCHID, { gasLimit: 6721975, gasPrice:0 })
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
    let tx = await ethereum.provider.getTransaction(e.transactionHash)
    if (!tx) {
      next(ApiError.internal('Unknown blockchain error'));
      return
    } else {
      var reason = ""
      if (ethereum.ethClient == "besu") {
        var result = await ethHelper.makeReceiptCall(e.transactionHash)
        var revert = result.data.result.revertReason
        reason = ethHelper.translateHexToString(138, revert)
      }
      else if (ethereum.ethClient == "iota_evm") {
        reason = await temp_error(tx)
      }
      else {
        let code = await ethereum.provider.call(tx, tx.blockNumber)
        reason = ethHelper.translateHexToString(138, code)
      }
      reason = reason.replace(/\0.*$/g, ''); //delete null characters of a string
      next(ApiError.badRequest(reason));
      return
    }
  }
})

.post("/deRegisterDevice", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /deRegisterDevice with chid: ${parameters.deviceCHID}`)

    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    if (check_undefined_params([parameters.deviceCHID])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      //TODO: catch error if not found
      const credential = await iota.get_credential(parameters.api_token, [OPERATOR], parameters.deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")
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

      var existingDeviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)

      if (!ethHelper.is_device_address_valid(existingDeviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
        (existingDeviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

      var txResponse = await depositDeviceContract.deRegisterDevice(parameters.deviceCHID, { gasLimit: 6721975, gasPrice:0 })
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
    let tx = await ethereum.provider.getTransaction(e.transactionHash)
    if (!tx) {
      next(ApiError.internal('Unknown blockchain error'));
      return
    } else {
      var reason = ""
      if (ethereum.ethClient == "besu") {
        var result = await ethHelper.makeReceiptCall(e.transactionHash)
        var revert = result.data.result.revertReason
        reason = ethHelper.translateHexToString(138, revert)
      }
      else if (ethereum.ethClient == "iota_evm") {
        reason = await temp_error(tx)
      }
      else {
        let code = await ethereum.provider.call(tx, tx.blockNumber)
        reason = ethHelper.translateHexToString(138, code)
      }
      reason = reason.replace(/\0.*$/g, ''); //delete null characters of a string
      next(ApiError.badRequest(reason));
      return
    }
  }
})

.post("/issuePassport", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /issuePassport with DPP: ${parameters.deviceDPP}`)
    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    //why check for issuerid, documentid and documentsignature if they are optional?
    //if (check_undefined_params([parameters.deviceDPP, parameters.issuerID, parameters.documentID, parameters.documentSignature])) {
    if (check_undefined_params([parameters.deviceDPP])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }
    var splitDeviceDPP = parameters.deviceDPP.split(":");
    const deviceCHID = splitDeviceDPP[0];
    const devicePHID = splitDeviceDPP[1];

    if (devicePHID == "" || splitDeviceDPP.length != 2) {
      next(ApiError.badRequest('Incorrect DPP format'));
      return
    }

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      const credential = await iota.get_credential(parameters.api_token, [OPERATOR,WITNESS], deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")

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
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

      const txResponse = await depositDeviceContract.issuePassport(deviceCHID, devicePHID, parameters.documentID, parameters.documentSignature, parameters.issuerID, { gasLimit: 6721975, gasPrice:0 })
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
    let tx = await ethereum.provider.getTransaction(e.transactionHash)
    if (!tx) {
      next(ApiError.internal('Unknown blockchain error'));
      return
    } else {
      var reason = ""
      if (ethereum.ethClient == "besu") {
        var result = await ethHelper.makeReceiptCall(e.transactionHash)
        var revert = result.data.result.revertReason
        reason = ethHelper.translateHexToString(138, revert)
      }
      else if (ethereum.ethClient == "iota_evm") {
        reason = await temp_error(tx)
      }
      else {
        let code = await ethereum.provider.call(tx, tx.blockNumber)
        reason = ethHelper.translateHexToString(138, code)
      }
      reason = reason.replace(/\0.*$/g, ''); //delete null characters of a string
      next(ApiError.badRequest(reason));
      return
    }
  }
})

.post("/generateProof", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /generateProof with chid: ${parameters.deviceCHID}`)
    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    if (check_undefined_params([parameters.deviceCHID])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }    
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }
    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      const credential = await iota.get_credential(parameters.api_token, [OPERATOR,WITNESS], parameters.deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")

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
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

      const txResponse = await depositDeviceContract.generateGenericProof(parameters.deviceCHID, parameters.issuerID, parameters.documentID, parameters.documentSignature, parameters.type, { gasLimit: 6721975, gasPrice:0 })
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
    let tx = await ethereum.provider.getTransaction(e.transactionHash)
    if (!tx) {
      next(ApiError.internal('Unknown blockchain error'));
      return
    } else {
      var reason = ""
      if (ethereum.ethClient == "besu") {
        var result = await ethHelper.makeReceiptCall(e.transactionHash)
        var revert = result.data.result.revertReason
        reason = ethHelper.translateHexToString(138, revert)
      }
      else if (ethereum.ethClient == "iota_evm") {
        reason = await temp_error(tx)
      }
      else {
        let code = await ethereum.provider.call(tx, tx.blockNumber)
        reason = ethHelper.translateHexToString(138, code)
      }
      reason = reason.replace(/\0.*$/g, ''); //delete null characters of a string
      next(ApiError.badRequest(reason));
      return
    }
  }
})

.post("/transferOwnership", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;
  try {
    console.log(`Called /transferOwnership with chid: ${parameters.deviceCHID} and newOwner ${parameters.newOwner}`)

    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    if (check_undefined_params([parameters.deviceCHID, parameters.newOwner])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }

    const target_valid = await multiacc.check_exists(parameters.newOwner)
    if(!target_valid) {
      next(ApiError.badRequest("New owner doesn't exist."));
      return
    }

    if (parameters.dlt == iota_name) {
      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }
      const iota_id = await iota.get_iota_id(parameters.api_token)
      const target_id = await iota.get_iota_id(parameters.newOwner)
      const credential = await iota.get_credential(parameters.api_token, [], parameters.deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")
      const new_owner_credential = await iota.transfer_ownership(iota_id,credential,target_id,parameters.deviceCHID)

      //current owner
      var currentOwnerData = await multiacc.get_acc_data(parameters.api_token)
      delete currentOwnerData.iota.credentials[OWNERSHIP][parameters.deviceCHID]
      await multiacc.set_acc_data(parameters.api_token, currentOwnerData)

      var targetUserData = await multiacc.get_acc_data(parameters.newOwner)
      //it must be possible to do this better (maybe)
      if (targetUserData.iota.credentials?.[OWNERSHIP] == undefined){
        targetUserData.iota.credentials[OWNERSHIP] = {[parameters.deviceCHID]: new_owner_credential}
      }
      else {
        targetUserData.iota.credentials[OWNERSHIP][parameters.deviceCHID] = new_owner_credential
      }
      await multiacc.set_acc_data(parameters.newOwner, targetUserData)

      response_data = {
        credential: new_owner_credential
      }

    }

    else if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)
      const new_owner_wallet = await ethHelper.get_wallet(parameters.newOwner)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)

      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

      const txResponse = await depositDeviceContract.transferDevice(new_owner_wallet.address, { gasLimit: 6721975, gasPrice:0 })
      const txReceipt = await txResponse.wait()
      var args = ethHelper.getEvents
      (txReceipt, 'transferProof', ethereum.depositDeviceIface)

      response_data = {
        oldOwner: args.supplierAddress,
        newOwner: args.receiverAddress,
        timestamp: parseInt(Number(args.timestamp), 10)
      }
    }

    res.status(200);
    res.json({
      data: response_data
    })
  }

  catch (e) {
    let tx = await ethereum.provider.getTransaction(e.transactionHash)
    if (!tx) {
      next(ApiError.internal('Unknown blockchain error'));
      return
    } else {
      var reason = ""
      if (ethereum.ethClient == "besu") {
        var result = await ethHelper.makeReceiptCall(e.transactionHash)
        var revert = result.data.result.revertReason
        reason = ethHelper.translateHexToString(138, revert)
      }
      else if (ethereum.ethClient == "iota_evm") {
        reason = await temp_error(tx)
      }
      else {
        let code = await ethereum.provider.call(tx, tx.blockNumber)
        reason = ethHelper.translateHexToString(138, code)
      }
      reason = reason.replace(/\0.*$/g, ''); //delete null characters of a string
      next(ApiError.badRequest(reason));
      return
    }
  }
})

.post("/getProofs", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /getProofs with chid: ${parameters.deviceCHID}`)
    is_dlt_valid(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      const credential = await iota.get_credential(parameters.api_token, [OPERATOR,WITNESS,VERIFIER], parameters.deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")

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
    is_dlt_valid(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      const credential = await iota.get_credential(parameters.api_token, [OPERATOR,WITNESS,VERIFIER], parameters.deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")

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

.post("/getTransferProofs", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /getTransferProofs with chid: ${parameters.deviceCHID}`)
    is_dlt_valid(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      const credential = await iota.get_credential(parameters.api_token, [OPERATOR,WITNESS,VERIFIER], parameters.deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")

      var iota_proofs = await iota.read_specific_device_proofs(iota_id, credential, parameters.deviceCHID, "proof_of_transfer")
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

      const value = await depositDeviceContract.getTrasferProofs();
      var data = []
      if (value.length != 0) {
        value.forEach(elem => {
          let proof_data = {
            OldOwner: elem[0],
            NewOwner: elem[1],
            timestamp: parseInt(Number(elem[2]), 10),
            blockNumber: parseInt(Number(elem[3]), 10),
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
    is_dlt_valid(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      const credential = await iota.get_credential(parameters.api_token, [OPERATOR,WITNESS,VERIFIER], parameters.deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")

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
    is_dlt_valid(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == iota_name) {
      const iota_id = await iota.get_iota_id(parameters.api_token)

      if ((await iota.lookup_device_channel(parameters.deviceCHID) == false)) {
        throw new BadRequest("CHID not registered.")
      }

      const credential = await iota.get_credential(parameters.api_token, [OPERATOR,WITNESS,VERIFIER], parameters.deviceCHID)
      if(credential == undefined) throw new BadRequest("No valid credential found.")

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

.post("/getDidData", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /getDidData with chid: ${parameters.deviceCHID}`)
    is_dlt_valid(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    // const valid_token = await multiacc.check_token(parameters.api_token)
    // if (!valid_token) throw new BadRequest("Invalid API token.")

    if (parameters.dlt == ethereum_name) {
      // const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", ethHelper.randomWallet())

      const value = await depositDeviceContract.getDidData();
      // var data = Object.assign({}, value)
      var data = {}
      data.contractAddress = value.contractAddress
      data.controller = value.controller
      data.chid = value.chid
      data.chainid = parseInt(Number(value.chainid), 10)
      data.services = []
      value.services.forEach(elem => {
        let tmp = {}
        tmp.endpoint = elem.endpoint
        tmp.description = elem.description
        tmp.type = elem.type_
        tmp.fragment = elem.fragment
        data.services.push(tmp)
      })

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

.post("/addService", async (req, res, next) => {
  const parameters = new Parameters(req)

  try {
    console.log(`Called /addService with chid: ${parameters.deviceCHID}`)
    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    if (check_undefined_params([parameters.deviceCHID, parameters.fragment, parameters.endpoint])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }    
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }
    if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

      const txResponse = await depositDeviceContract.addService(parameters.endpoint, parameters.type, parameters.description, parameters.fragment, { gasLimit: 6721975, gasPrice:0 })
      const txReceipt = await txResponse.wait()
    }

    res.status(201);
    res.json({
    })

  }
  catch (e) {
    let tx = await ethereum.provider.getTransaction(e.transactionHash)
    if (!tx) {
      next(ApiError.internal('Unknown blockchain error'));
      return
    } else {
      var reason = ""
      if (ethereum.ethClient == "besu") {
        var result = await ethHelper.makeReceiptCall(e.transactionHash)
        var revert = result.data.result.revertReason
        reason = ethHelper.translateHexToString(138, revert)
      }
      else if (ethereum.ethClient == "iota_evm") {
        reason = await temp_error(tx)
      }
      else {
        let code = await ethereum.provider.call(tx, tx.blockNumber)
        reason = ethHelper.translateHexToString(138, code)
      }
      reason = reason.replace(/\0.*$/g, ''); //delete null characters of a string
      next(ApiError.badRequest(reason));
      return
    }
  }
})

.post("/removeService", async (req, res, next) => {
  const parameters = new Parameters(req)

  try {
    console.log(`Called /removeService with chid: ${parameters.deviceCHID}`)
    if (!is_dlt_valid(parameters.dlt, parameters.deviceCHID)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    if (check_undefined_params([parameters.deviceCHID, parameters.fragment])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }    
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }
    if (parameters.dlt == ethereum_name) {
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, "../../../build/contracts/DepositDevice.json", wallet)

      const txResponse = await depositDeviceContract.removeService(parameters.fragment, { gasLimit: 6721975, gasPrice:0 })
      const txReceipt = await txResponse.wait()
    }

    res.status(201);
    res.json({
    })

  }
  catch (e) {
    let tx = await ethereum.provider.getTransaction(e.transactionHash)
    if (!tx) {
      next(ApiError.internal('Unknown blockchain error'));
      return
    } else {
      var reason = ""
      if (ethereum.ethClient == "besu") {
        var result = await ethHelper.makeReceiptCall(e.transactionHash)
        var revert = result.data.result.revertReason
        reason = ethHelper.translateHexToString(138, revert)
      }
      else if (ethereum.ethClient == "iota_evm") {
        reason = await temp_error(tx)
      }
      else {
        let code = await ethereum.provider.call(tx, tx.blockNumber)
        reason = ethHelper.translateHexToString(138, code)
      }
      reason = reason.replace(/\0.*$/g, ''); //delete null characters of a string
      next(ApiError.badRequest(reason));
      return
    }
  }
})

module.exports = router
