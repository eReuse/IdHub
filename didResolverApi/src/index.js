import express from 'express'
import bodyParser from 'body-parser'

import resolution from './resolution.js'

const app = express()
app.use(bodyParser.json())
app.use(
    bodyParser.urlencoded({
        extended: true,
    })
)

const port = 3011
const host = "0.0.0.0"

app.use("/", resolution)

app.listen(port, host, () => {
    console.log(`Example app listening at http://${host}:${port}`)
})

//module.exports = app
