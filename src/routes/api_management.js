const express = require('express'),
router = express.Router();

const ApiError = require('../utils/apiError')
const storage = require('node-persist');
const ethers = require("ethers")
const multiacc = require("../utils/multiacc-helper.js");
const ethereum = require("../utils/ethereum/ethereum-config.js")
const ethHelper = require("../utils/ethereum/ethereum-helper.js")



const app = express()

router

.post("/registerUser", async (req, res, next) => {
    const privateKey = req.body?.privateKey ?? ""
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

      await storage.setItem(token_object.prefix, { salt: token_object.salt, hash: token_object.hash, eth_priv_key: wallet.privateKey})
      res.status(201);
      res.json({
        status: "Success.",
        data: {
          api_token: token_object.token,
          eth_pub_key: wallet.address,
          eth_priv_key: wallet.privateKey
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

      const valid_token = await multiacc.check_token(api_token)
      if (!valid_token) {
          next(ApiError.badRequest('Invalid API token'));
          return
      } 

      const wallet = await ethHelper.get_wallet(api_token)
      
      const accessListContract = ethHelper.createContract
      (ethereum.ACCESSLIST_ADDRESS, ethereum.AccessList, wallet)

      const isIssuer = await accessListContract.checkIfIssuer(wallet.address);
      const isOperator = await accessListContract.checkIfOperator(wallet.address);
      const isWitness = await accessListContract.checkIfWitness(wallet.address);
      const isVerifier = await accessListContract.checkIfVerifier(wallet.address);

      var response_data_eth = {
        walletAddress: wallet.address,
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
