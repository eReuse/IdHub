import {getResolver} from '../../didResolverModule/src/ereuseResolver.js'
import  {Resolver} from 'did-resolver'

import express from 'express'
var router = express.Router();

import dotenv from "dotenv"
dotenv.config()

router

.get('/*', async (req, res) => {
    const eReuseResolver = getResolver(process.env.API_CONNECTOR_URL)
    const didResolver = new Resolver(eReuseResolver)
    const doc = await didResolver.resolve(req.url.substring(1))
    res.send(JSON.stringify(doc, null, 2))
})

export default router;