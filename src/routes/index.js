const express = require("express")
var bodyParser = require('body-parser')

const app = express()
app.use(bodyParser.json())
app.use(
  bodyParser.urlencoded({
    extended: true,
  })
)

const port = 3010
const host = "0.0.0.0"

app.use("/", require("./devices"))
app.use("/", require("./api_management"))

app.listen(port, host, () => {
    console.log(`Example app listening at http://${host}:${port}`)
  })

module.exports = app
