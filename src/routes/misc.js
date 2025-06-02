const express = require('express'),
    router = express.Router();

const ethereum = require("../utils/ethereum/ethereum-config.js")
const ethHelper = require("../utils/ethereum/ethereum-helper.js")

router
    .get("/getTa", async (req, res, next) => {
        try {
            const accessListContract = ethHelper.createContract
            (ethereum.ACCESSLIST_ADDRESS, ethereum.AccessList, ethHelper.randomWallet())

            const root_pub_key = await accessListContract.checkTA();

            res.status(200);
            res.json({
                status: "Success.",
                data: {
                    root_pub_key: root_pub_key
                }
            })
        }
        catch (e) {
            console.log(e)
            next(e);
        }
    })
    .get("/getChainId", async (req, res, next) => {
        try {
            const chain_id = ethereum.chainId;

            res.status(200);
            res.json({
                status: "Success.",
                data: {
                    chain_id: chain_id
                }
            })
        }
        catch (e) {
            console.log(e)
            next(e);
        }
    })

module.exports = router
