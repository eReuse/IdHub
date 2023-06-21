const express = require('express'),
router = express.Router();

const ApiError = require('../utils/apiError')
const storage = require('node-persist');
const ethers = require("ethers")
const iota = require("../utils/iota/iota-helper.js")
const multiacc = require("../utils/multiacc-helper.js");
const ethereum = require("../utils/ethereum/ethereum-config.js")
const ethHelper = require("../utils/ethereum/ethereum-helper.js")



const app = express()

router

.post("/registerUser", async (req, res, next) => {
    const privateKey = req.body.privateKey ?? ""
    var wallet
    try {
      console.log(`Called /registerUser`)
      const token_object = multiacc.generate_token()
      if (privateKey == "") {
        wallet = ethers.Wallet.createRandom()
      }
      else {
        var re = /[0-9A-Fa-f]{6}/g;
        if((!re.test(privateKey)) || (privateKey.length != 64)) {
          next(ApiError.badRequest('Invalid PrivateKey format'));
          return
        }
        wallet = new ethers.Wallet(privateKey, ethereum.provider)
      }
      
      const send_eth_tx={
      	from: ethereum.signer.address,
      	to: wallet.address,
      	value: ethers.utils.parseEther("0.1"),
      	nonce: ethereum.provider.getTransactionCount(ethereum.signer.address, "latest"),
      	gasLimit: ethers.utils.hexlify(50000),
      	gasPrice: 0
      }
      
      let res_eth = await ethereum.signer.sendTransaction(send_eth_tx)
      var txReceipt = await res_eth.wait()

      //Creation of IOTA identity.
      //TODO: check if it's provided in request.
      
      //IOTA DOWN atm, placeholder
      var iota_id = "iota_placeholder"
      //var iota_id = await iota.create_identity()

      await storage.setItem(token_object.prefix, { salt: token_object.salt, hash: token_object.hash, eth_priv_key: wallet.privateKey, iota_id: iota_id, iota: {credentials:{}}})
      res.status(201);
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
      console.log(e)
      next(e);
    }
  
  })
  
.post("/invalidateUser", async (req, res, next) => {
    const api_token = req.body.api_token;
    try {
      console.log(`Called /invalidateUser`)
      const deleted = await multiacc.delete_token(api_token)
      if (!deleted) {
        next(ApiError.badRequest('Invalid API token'));
        return
      }
      res.status(200)
      res.json({
        status: "Success.",
        data: {
          deleted_token: api_token
        }
      })
    }
    catch (e) {
      console.log(e)
      next(e);
    }
  
})

.post("/checkUserRoles", async (req, res, next) => {
    const api_token = req.body.api_token;
    console.log(`Called /checkUserRoles`)
    try {
      //TODO: check IOTA roles. store output into iota_response_data

      const valid_token = await multiacc.check_token(api_token)
      if (!valid_token) {
          next(ApiError.badRequest('Invalid API token'));
          return
      } 

      const wallet = await ethHelper.get_wallet(api_token)
      
      const accessListContract = ethHelper.createContract
      (ethereum.ACCESSLIST_ADDRESS, "../../../build/contracts/AccessList.json", wallet)

      const isIssuer = await accessListContract.checkIfIssuer(wallet.address);
      const isOperator = await accessListContract.checkIfOperator(wallet.address);
      const isWitness = await accessListContract.checkIfWitness(wallet.address);
      const isVerifier = await accessListContract.checkIfVerifier(wallet.address);

      var response_data_eth = {
        isIssuer: isIssuer,
        isOperator: isOperator,
        isWitness: isWitness,
        isVerifier: isVerifier,
      }
      
      res.status(200);
      res.json({
        status: "Success.",
        data: response_data_eth
      })
    }

    catch (e) {
      console.log(e)
      next(e);
    }
  })

module.exports = router
