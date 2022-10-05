import { Resolver } from 'did-resolver'
import util from 'util'
import { getResolver } from './ereuseResolver.js'

const eReuseResolver = getResolver("http://127.0.0.1:3010")
const didResolver = new Resolver(eReuseResolver)

const doc = await didResolver.resolve('did:ereuse:example1')
//console.log(JSON.stringify(doc, null, 2))
console.log(util.inspect(doc, { colors: true, depth: 3 }));