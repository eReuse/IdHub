const express = require('express'),
router = express.Router();

const { BadRequest, NotFound, Forbidden } = require("../utils/errors")
const storage = require('node-persist');
const ethers = require("ethers")
const iota = require("../utils/iota/iota-helper.js")
const multiacc = require("../utils/multiacc-helper.js");
const ethereum = require("../utils/ethereum/ethereum-config.js")

const app = express()

const ethereum_name = "ethereum"
const iota_name = "iota"
const cosmos_name = "cosmos"

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

    .post("/requestCredential", async (req, res, next) => {
        const api_token = req.body.api_token;
        const credentialType = req.body.CredentialType;
        const dlt = req.headers.dlt ?? "";
        var response_data
        try {
            console.log(`Called /requestCredential`)

            check_dlt(dlt)
            const valid_token = await multiacc.check_token(api_token)
            if (!valid_token) throw new BadRequest("Invalid API token.")

            if (dlt == iota_name) {
                const iota_id = await iota.get_iota_id(api_token)

                var credential = await iota.issue_credential(iota_id, credentialType)

                var userData = await multiacc.get_acc_data(api_token)
                //it must be possible to do this better (maybe)
                userData.iota.credentials[credentialType] = credential

                await multiacc.set_acc_data(api_token, userData)

                response_data = {
                    credential: credential,
                }
            }

            else if (dlt == ethereum_name) {
                //TODO
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