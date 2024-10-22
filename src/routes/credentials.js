const express = require('express'),
    router = express.Router();

const { BadRequest, NotFound, Forbidden } = require("../utils/errors")
const ApiError = require('../utils/apiError')
const ethers = require("ethers")
const multiacc = require("../utils/multiacc-helper.js");
const ethereum = require("../utils/ethereum/ethereum-config.js")
const ethHelper = require("../utils/ethereum/ethereum-helper.js")
const { OPERATOR, WITNESS, VERIFIER, OWNERSHIP, ISSUER } = require('../utils/constants')
const axios = require("axios")

const app = express()

const ethereum_name = "ethereum"

const credential_types = ["Operator", "Witness", "Verifier", "Issuer"]

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
    if (!dlt == ethereum_name) {
        throw new BadRequest("Invalid DLT identifier")
    }
}

router

    // .post("/setIssuer", async (req, res, next) => {
    //     const api_token = req.body.api_token ?? "";
    //     const target_user = req.body.target_user ?? "";
    //     const dlt = req.headers.dlt ?? "";
    //     var response_data
    //     try {
    //         console.log(`Called /setIssuer`)

    //         check_dlt(dlt)
    //         // const admin_token = await multiacc.check_admin(api_token)
    //         // if (!admin_token) {
    //         //     next(ApiError.badRequest('Need admin token.'));
    //         //     return
    //         // }
    //         const valid_token = await multiacc.check_token(api_token)
    //         if (!valid_token) {
    //             next(ApiError.badRequest('Invalid API token.'));
    //             return
    //         }
    //         const target_valid = await multiacc.check_exists(target_user)
    //         if (!target_valid) {
    //             next(ApiError.badRequest('Target user doesnt exist.'));
    //             return
    //         }

    //         if (dlt == iota_name) {
    //             const target_iota_id = await iota.get_iota_id(target_user)
    //             var credential = await iota.issue_credential(target_iota_id, ISSUER)
    //             var target_data = await multiacc.get_acc_data(target_user)
    //             //it must be possible to do this better (maybe)
    //             target_data.iota.credentials[ISSUER] = credential
    //             await multiacc.set_acc_data(target_user, target_data)
    //             response_data = {
    //                 credential: credential,
    //             }
    //         }

    //         else if (dlt == ethereum_name) {
    //             const admin_wallet = await ethHelper.get_wallet(api_token)
    //             const accessListConstract = ethHelper.createContract
    //                 (ethereum.ACCESSLIST_ADDRESS, "../../../build/contracts/AccessList.json", admin_wallet)
    //             const target_eth_wallet = await ethHelper.get_wallet(target_user)
    //             var txResponse = await accessListConstract.registerIssuer(target_eth_wallet.address, { gasLimit: 6721975, gasPrice:0 })
    //             var txReceipt = await txResponse.wait()
    //             response_data = {}
    //         }

    //         res.status(201);
    //         res.json({
    //             status: "Success.",
    //             data: response_data
    //         })
    //     }
    //     catch (e) {
    //         console.log(e)
    //         next(e);
    //     }
    // })

    .post("/oracle", async (req, res, next) => {
        const api_token = req.body.api_token;
        const verifiableCredential = req.body.Credential;
        const credentialType = verifiableCredential.credentialSubject.role
        const target_user = verifiableCredential.credentialSubject.id.slice(9)
        const dlt = req.headers.dlt ?? "";
        var response_data
        try {
            console.log(`Called /oracle for target user ${target_user} and credential type ${credentialType}`)

            check_dlt(dlt)
            const valid_token = await multiacc.check_token(api_token)
            if (!valid_token) {
                next(ApiError.badRequest("Invalid API token."));
                return
            }

            var verify_result = await axios.post(`${ethereum.veramoURL}/verify`,{
                credential: verifiableCredential
            })
            
            if(verify_result.data.data != true){
                next(ApiError.badRequest("Verifiable credential is invalid."));
                return
            }
            const issuer_eth_wallet = await ethHelper.get_wallet(api_token)
            // const target_eth_wallet = await ethHelper.get_wallet(target_user)
            const accessListConstract = ethHelper.createContract
                (ethereum.ACCESSLIST_ADDRESS, ethereum.AccessList, issuer_eth_wallet)
            var txResponse
            if (credentialType == "operator")
                txResponse = await accessListConstract.registerOperator(target_user, { gasLimit: 6721975, gasPrice: 0 })
            if (credentialType == "witness")
                txResponse = await accessListConstract.registerWitness(target_user, { gasLimit: 6721975, gasPrice: 0 })
            if (credentialType == "verifier")
                txResponse = await accessListConstract.registerVerifier(target_user, { gasLimit: 6721975, gasPrice: 0 })
            if (credentialType == "issuer")
                txResponse = await accessListConstract.registerIssuer(target_user, { gasLimit: 6721975, gasPrice: 0 })
            var txReceipt = await txResponse.wait()
            response_data = {}

            res.status(201);
            res.json({
                status: "Success.",
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

    .post("/getCredentials", async (req, res, next) => {
        const target_user_eth_address = req.body.target_user;
        const credentialType = req.body.CredentialType;
        const dlt = req.headers.dlt ?? "";
        var response_data
        try {
            console.log(`Called /getCredentials`)

            check_dlt(dlt)
            if (!credential_types.includes(credentialType)) {
                next(ApiError.badRequest("Invalid credential type."));
                return
            }

            if (dlt == ethereum_name) {
                const accessListContract = ethHelper.createContract
                    (ethereum.ACCESSLIST_ADDRESS, ethereum.AccessList, ethHelper.randomWallet())
                var txResponse
                if (credentialType == "Operator")
                    txResponse = await accessListContract.get_operator_credentials(target_user_eth_address, { gasLimit: 6721975, gasPrice:0 })
                if (credentialType == "Witness")
                    txResponse = await accessListContract.get_witness_credentials(target_user_eth_address, { gasLimit: 6721975, gasPrice:0 })
                if (credentialType == "Verifier")
                    txResponse = await accessListContract.get_verifier_credentials(target_user_eth_address, { gasLimit: 6721975, gasPrice:0 })
                if (credentialType == "Issuer")
                    txResponse = await accessListContract.get_issuer_credentials(target_user_eth_address, { gasLimit: 6721975, gasPrice:0 })
                response_data = txResponse
            }

            res.status(201);
            res.json({
                status: "Success.",
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

module.exports = router