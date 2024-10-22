const express = require("express")
const cors = require('cors')
var bodyParser = require('body-parser')
const apiErrorHandler = require('./utils/apiErrorHandler')
const apiInitializer = require('./utils/apiInitializer')

const userRouter = require('./routes/api_management')
const devicesRouter = require('./routes/devices')
const credentialsRouter = require('./routes/credentials')

const app = express()
app.use(bodyParser.json())
app.use(
  bodyParser.urlencoded({
    extended: true,
  })
)
app.use(cors())

const port = 3010
const host = "0.0.0.0"

apiInitializer.initial_steps();

app.use("/", userRouter)
app.use("/", devicesRouter)
app.use("/", credentialsRouter)

app.use(apiErrorHandler);


app.listen(port, host, () => {
    console.log(`Example app listening at http://${host}:${port}`)
  })

module.exports = app
