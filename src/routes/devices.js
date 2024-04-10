const express = require('express'),
router = express.Router();

//const { BadRequest, NotFound, Forbidden } = require("../utils/errors")
const ApiError = require('../utils/apiError')


const ethereum = require("../utils/ethereum/ethereum-config.js")
const ethHelper = require("../utils/ethereum/ethereum-helper.js")
const multiacc = require("../utils/multiacc-helper.js");
const CryptoJS = require('crypto-js')
const axios = require('axios')

const {
  sha3_512,
  sha3_384,
  sha3_256,
  sha3_224,
  keccak512,
  keccak384,
  keccak256,
  keccak224,
  shake128,
  shake256,
  cshake128,
  cshake256,
  kmac128,
  kmac25
} = require('js-sha3');

const {OPERATOR, WITNESS, VERIFIER, OWNERSHIP} = require('../utils/constants')


const ethereum_name = "ethereum"


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
    this.documentHashAlgorithm = req.body.DocumentHashAlgorithm ?? "";
    this.documentHash = req.body.DocumentHash ?? "";
    this.issuerID = req.body.IssuerID ?? "";
    this.type = req.body.Type ?? "";
    this.dlt = req.headers.dlt ?? "";
    this.newOwner = req.body.NewOwner ?? "";
    this.endpoint = req.body.endpoint ?? "";
    this.description = req.body.description ?? "";
    this.fragment = req.body.fragment ?? "";
    this.inventoryID=req.body.InventoryID ?? "";
    //this.dlt = req.headers.dlt.replace(/\s+/g, '').split(',')
    this.documentID = req.body.DocumentID ?? "";
    this.documentSignature = req.body.DocumentSignature ?? "";
    this.timestamp = req.body.Timestamp ?? "";
    this.amount = req.body.Amount ?? "";
    this.address = req.body.Address ?? "";
    this.credential = req.body.Credential ?? "";
  }
}

function is_dlt_valid(dlt) {
  if (dlt == ethereum_name) {
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
    if (check_undefined_params([parameters.deviceCHID, parameters.documentHash, parameters.documentHashAlgorithm, parameters.inventoryID])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }


    const wallet = await ethHelper.get_wallet(parameters.api_token)
    var existingDeviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
    if (ethHelper.is_device_address_valid(existingDeviceAddress)) {
      next(ApiError.badRequest('Device already exists'));
      return
    }

    const deviceFactoryContract = ethHelper.createContract
      (ethereum.DEVICEFACTORY_ADDRESS, ethereum.DeviceFactory, wallet)
    var txResponse = await deviceFactoryContract.registerDevice(parameters.deviceCHID, parameters.documentHashAlgorithm, parameters.documentHash, parameters.inventoryID, { gasLimit: 6721975, gasPrice: 0 })
    var txReceipt = await txResponse.wait()
    var args = ethHelper.getEvents
      (txReceipt, 'DeviceRegistered', ethereum.deviceFactoryIface)

    response_data = {
      deviceAddress: args._deviceAddress,
      timestamp: parseInt(Number(args.timestamp), 10)
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
      else {
        // let code = await ethereum.provider.call(tx, tx.blockNumber)
        // reason = ethHelper.translateHexToString(138, code)
        reason = "Error: couldn't retrieve a reason."
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

    


      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var existingDeviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)

      if (!ethHelper.is_device_address_valid(existingDeviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
        (existingDeviceAddress, ethereum.DepositDevice, wallet)

      var txResponse = await depositDeviceContract.deRegisterDevice(parameters.deviceCHID, { gasLimit: 6721975, gasPrice:0 })
      var txReceipt = await txResponse.wait()

      var args = ethHelper.getEvents
        (txReceipt, 'deRegisterProof', ethereum.depositDeviceIface)
      response_data = {
        timestamp: parseInt(Number(args.timestamp), 10)
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
    if (check_undefined_params([parameters.deviceDPP, parameters.documentHash, parameters.documentHashAlgorithm, parameters.inventoryID])) {
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

    


      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(deviceCHID)

      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

      const txResponse = await depositDeviceContract.issuePassport(devicePHID, parameters.documentHashAlgorithm, parameters.documentHash, parameters.inventoryID, { gasLimit: 6721975, gasPrice:0 })
      const txReceipt = await txResponse.wait()
      var args = ethHelper.getEvents
      (txReceipt, 'genericProof', ethereum.depositDeviceIface)

      response_data = {
        timestamp: parseInt(Number(args.timestamp), 10)
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

.post("/mintTokens", async (req, res, next) => {
  const parameters = new Parameters(req)

  try {
    console.log(`Called /mintTokens to address: ${parameters.address}`)
    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }

    if (check_undefined_params([parameters.address])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }

    const wallet = await ethHelper.get_wallet(parameters.api_token)

    const tokenContract = ethHelper.createContract
      (ethereum.TOKEN_CONTRACT_ADDRESS, ethereum.TokenContract, wallet)

    const txResponse = await tokenContract.mint(parameters.address, { gasLimit: 6721975, gasPrice: 0 })
    await txResponse.wait()

    res.status(200);
    res.json({
      data: "Success"
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

.post("/allowTokens", async (req, res, next) => {
  const parameters = new Parameters(req)

  try {
    console.log(`Called /allowTokens with amount: ${parameters.amount}`)
    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }

    if (check_undefined_params([parameters.amount])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }

    const wallet = await ethHelper.get_wallet(parameters.api_token)

    const tokenContract = ethHelper.createContract
      (ethereum.TOKEN_CONTRACT_ADDRESS, ethereum.TokenContract, wallet)

    const txResponse = await tokenContract.approve(ethereum.DEVICEFACTORY_ADDRESS, 1000000, { gasLimit: 6721975, gasPrice: 0 })
    await txResponse.wait()

    res.status(200);
    res.json({
      data: "Success"
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

.post("/releaseTokens", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /releaseTokens with CHID: ${parameters.deviceCHID} to address: ${parameters.address}`)
    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    //why check for issuerid, documentid and documentsignature if they are optional?
    //if (check_undefined_params([parameters.deviceDPP, parameters.issuerID, parameters.documentID, parameters.documentSignature])) {
    if (check_undefined_params([parameters.deviceCHID, parameters.address])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }

    const wallet = await ethHelper.get_wallet(parameters.api_token)

    var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)

    if (!ethHelper.is_device_address_valid(deviceAddress)) {
      next(ApiError.badRequest('CHID not registered'));
      return
    }

    const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

    const txResponse = await depositDeviceContract.releaseFunds(parameters.address, { gasLimit: 6721975, gasPrice: 0 })
    const txReceipt = await txResponse.wait()
    var args = ethHelper.getEvents
      (txReceipt, 'fundsReleased', ethereum.depositDeviceIface)

    response_data = {
      from: args[0],
      to: args[1]
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

.get("/balanceOf", async (req, res, next) => {
  var chid = req.query.chid

  try {
    console.log(`Called /balanceOf with chid: ${chid}`)

    var deviceAddress = await ethHelper.chid_to_deviceAdress(chid)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

    const wallet = ethHelper.randomWallet()

    const tokenContract = ethHelper.createContract
      (ethereum.TOKEN_CONTRACT_ADDRESS, ethereum.TokenContract, wallet)

    const balance = await tokenContract.balanceOf(deviceAddress);


    res.status(200);
    res.json({
      balance: parseInt(balance, 10),
      address: deviceAddress
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
    if (!is_dlt_valid(parameters.dlt)) {
      next(ApiError.badRequest('Invalid DLT identifier'));
      return
    }
    if (check_undefined_params([parameters.deviceCHID,parameters.inventoryID])) {
      next(ApiError.badRequest('Invalid Syntax.'));
      return
    }    
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) {
      next(ApiError.badRequest('Invalid API token'));
      return
    }

      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

      const txResponse = await depositDeviceContract.generateGenericProof(parameters.documentHashAlgorithm, parameters.documentHash, parameters.type, parameters.inventoryID, { gasLimit: 6721975, gasPrice:0 })
      const txReceipt = await txResponse.wait()
      var args = ethHelper.getEvents
      (txReceipt, 'genericProof', ethereum.depositDeviceIface)

      response_data = {
        timestamp: parseInt(Number(args.timestamp), 10)
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


      const wallet = await ethHelper.get_wallet(parameters.api_token)
      const new_owner_wallet = await ethHelper.get_wallet(parameters.newOwner)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)

      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

      const txResponse = await depositDeviceContract.transferDevice(new_owner_wallet.address, { gasLimit: 6721975, gasPrice:0 })
      const txReceipt = await txResponse.wait()
      var args = ethHelper.getEvents
      (txReceipt, 'transferProof', ethereum.depositDeviceIface)

      response_data = {
        oldOwner: args.supplierAddress,
        newOwner: args.receiverAddress,
        timestamp: parseInt(Number(args.timestamp), 10)
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
    if (!valid_token) {
      next(ApiError.badRequest("Invalid API token."))
      return;
    }


      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest("CHID not registered"))
        return;
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

      const value = await depositDeviceContract.getGenericProofs();
      var data = []
      if (value.length != 0) {
        value.forEach(elem => {
          let proof_data = {
            chid: elem[0],
            phid: elem[1],
            IssuerID: elem[2],
            InventoryID: elem[3],
            DocumentHashAlgorithm: elem[4],
            DocumentHash: elem[5],
            Type: elem[6],
            timestamp: parseInt(Number(elem[7]), 10),
            blockNumber: parseInt(Number(elem[8]), 10),
          }
          data.push(proof_data)
        })
      }
      response_data = data


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

.post("/getDPPs", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /getDPPs with chid: ${parameters.deviceCHID}`)
    is_dlt_valid(parameters.dlt)
    check_undefined_params([parameters.deviceCHID])
    const valid_token = await multiacc.check_token(parameters.api_token)
    if (!valid_token) throw new BadRequest("Invalid API token.")


      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

      const value = await depositDeviceContract.getDPPs();
      var data = []
      if (value.length != 0) {
        value.forEach(elem => {
          data.push(`${parameters.deviceCHID}:${elem}`)
        })
      }
      response_data = data

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


      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

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



      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

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


      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
        (deviceAddress, ethereum.DepositDevice, wallet)

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


      // const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        throw new BadRequest("CHID not registered.")
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, ethHelper.randomWallet())

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
      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

      const txResponse = await depositDeviceContract.addService(parameters.endpoint, parameters.type, parameters.description, parameters.fragment, { gasLimit: 6721975, gasPrice:0 })
      const txReceipt = await txResponse.wait()


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

      const wallet = await ethHelper.get_wallet(parameters.api_token)

      var deviceAddress = await ethHelper.chid_to_deviceAdress(parameters.deviceCHID)
      if (!ethHelper.is_device_address_valid(deviceAddress)) {
        next(ApiError.badRequest('CHID not registered'));
        return
      }

      const depositDeviceContract = ethHelper.createContract
      (deviceAddress, ethereum.DepositDevice, wallet)

      const txResponse = await depositDeviceContract.removeService(parameters.fragment, { gasLimit: 6721975, gasPrice:0 })
      const txReceipt = await txResponse.wait()

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

.post("/verifyProof", async (req, res, next) => {
  const parameters = new Parameters(req)
  var response_data;

  try {
    console.log(`Called /verifyProof with chid: ${parameters.deviceCHID}`)
    check_undefined_params([parameters.documentHash,parameters.inventoryID, parameters.timestamp])

    var inventoryURL = await axios.get(ethereum.idIndexURL+"/getURL?id="+parameters.inventoryID)
    inventoryURL = inventoryURL.data.url

    var proof = await axios.get(inventoryURL+"/proofs/"+parameters.timestamp)
    var algorithm = proof.data.data.algorithm
    var document = proof.data.data.document

    var hash = sha3_256(document).toString(CryptoJS.enc.Hex);

    var test = hash == parameters.documentHash

    response_data = test
    // response_data = data

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

module.exports = router
