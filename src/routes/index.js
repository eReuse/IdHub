const express = require("express")
const app = express()

app.use("/devices", require("./devices"))

module.exports = app
