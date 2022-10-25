import {getResolver} from '../../didResolverModule/ereuseResolver.js'
import  {Resolver} from 'did-resolver'

import express from 'express'
var router = express.Router();

router

.get('/*', async (req, res) => {
    const eReuseResolver = getResolver("http://trubloDemo_api_multiacc:3010")
    const didResolver = new Resolver(eReuseResolver)
    const doc = await didResolver.resolve(req.url.substring(1))
    res.send(JSON.stringify(doc, null, 2))
})

export default router;