const express = require('express'),
router = express.Router();

const { BadRequest, NotFound, Forbidden } = require("../utils/errors")
const storage = require('node-persist');
const ethers = require("ethers")
const iota = require("../utils/iota/iota-helper.js")
const multiacc = require("../utils/multiacc-helper.js");
const ethereum = require("../utils/ethereum/ethereum-config.js")
const ethHelper = require("../utils/ethereum/ethereum-helper.js")
const {OPERATOR, WITNESS, VERIFIER, OWNERSHIP, ISSUER} = require('../utils/constants')

const app = express()

const ethereum_name = "ethereum"
const iota_name = "iota"
const cosmos_name = "cosmos"

const credential_types = ["Operator", "Witness", "Verifier"]

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

function check_dlt(dlt) {
    // if (dlt.length != 1) {
    //   throw new BadRequest("Can only call one DLT at a time.")
    // }
    if (!dlt == iota_name && !dlt == ethereum_name) {
        throw new BadRequest("Invalid DLT identifier")
    }
}

router

    .post("/setIssuer", async (req, res, next) => {
        const api_token = req.body.api_token;
        const target_user = req.body.target_user;
        const dlt = req.headers.dlt ?? "";
        var response_data
        try{
            console.log(`Called /setIssuer`)

            check_dlt(dlt)
            const admin_token = await multiacc.check_admin(api_token)
            if(!admin_token) throw new BadRequest("Need admin token.")
            const valid_token = await multiacc.check_token(api_token)
            if (!valid_token) throw new BadRequest("Invalid API token.")
            const target_valid = await multiacc.check_exists(target_user)
            if(!target_valid) throw new BadRequest("Target user doesn't exist.")

            if (dlt == iota_name){
                const target_iota_id = await iota.get_iota_id(target_user)
                var credential = await iota.issue_credential(target_iota_id, ISSUER)
                var target_data = await multiacc.get_acc_data(target_user)
                //it must be possible to do this better (maybe)
                target_data.iota.credentials[ISSUER] = credential
                await multiacc.set_acc_data(target_user, target_data)
                response_data = {
                    credential: credential,
                }
            }

            else if (dlt == ethereum_name){
                const admin_wallet = await ethHelper.get_wallet(api_token)
                const accessListConstract = ethHelper.createContract
                    (ethereum.ACCESSLIST_ADDRESS, "../../../build/contracts/AccessList.json", admin_wallet)
                const target_eth_wallet= await ethHelper.get_wallet(target_user)
                var txResponse = await accessListConstract.registerIssuer(target_eth_wallet.address, { gasLimit: 6721975 })
                var txReceipt = await txResponse.wait()
                response_data={}
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

    .post("/issueCredential", async (req, res, next) => {
        const api_token = req.body.api_token;
        const target_user = req.body.target_user;
        const credentialType = req.body.CredentialType;
        const dlt = req.headers.dlt ?? "";
        var response_data
        try {
            console.log(`Called /issueCredential`)

            check_dlt(dlt)
            const valid_token = await multiacc.check_token(api_token)
            if (!valid_token) throw new BadRequest("Invalid API token.")
            if (!credential_types.includes(credentialType)) throw new BadRequest("Invalid credential type.")
            const target_valid = await multiacc.check_exists(target_user)
            if(!target_valid) throw new BadRequest("Target user doesn't exist.")

            if (dlt == iota_name) {
                const issuer_credential = await iota.get_credential(api_token, [ISSUER])
                if (issuer_credential == undefined) throw new BadRequest("User is not issuer.")
                const target_iota_id = await iota.get_iota_id(target_user)
                var credential = await iota.issue_credential(target_iota_id, credentialType)
                var target_data = await multiacc.get_acc_data(target_user)
                //it must be possible to do this better (maybe)
                target_data.iota.credentials[credentialType] = credential
                await multiacc.set_acc_data(target_user, target_data)
                response_data = {
                    credential: credential,
                }
            }

            else if (dlt == ethereum_name) {
                const issuer_eth_wallet = await ethHelper.get_wallet(api_token)
                const target_eth_wallet= await ethHelper.get_wallet(target_user)
                const accessListConstract = ethHelper.createContract
                    (ethereum.ACCESSLIST_ADDRESS, "../../../build/contracts/AccessList.json", issuer_eth_wallet)
                var txResponse
                if (credentialType == "Operator")
                    txResponse = await accessListConstract.registerOperator(target_eth_wallet.address, { gasLimit: 6721975 })
                if (credentialType == "Witness")
                    txResponse = await accessListConstract.registerWitness(target_eth_wallet.address, { gasLimit: 6721975 })
                if (credentialType == "Verifier")
                    txResponse = await accessListConstract.registerVerifier(target_eth_wallet.address, { gasLimit: 6721975 })
                var txReceipt = await txResponse.wait()
                response_data={}
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

module.exports = router