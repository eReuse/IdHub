const express = require("express")
var bodyParser = require('body-parser')
const apiErrorHandler = require('./utils/apiErrorHandler')
const endpoints = require('./endpoints.js')

const app = express()
app.use(bodyParser.json())
app.use(
    bodyParser.urlencoded({
        extended: true,
    })
)

const port = 3012
const host = "0.0.0.0"

const fs = require('fs');
const path = require('path');

function checkOrCreateJSONFile() {
  const dataDir = '../data';
  const filePath = path.join(dataDir, 'id_url.json');

  try {
    // Check if the data directory exists
    fs.accessSync(dataDir);

    // Data directory exists, check if file exists
    fs.accessSync(filePath);

    // File exists, do nothing
    console.log('INDEX exists.');
  } catch (error) {
    // File or data directory doesn't exist, create them
    console.log('File or data directory does not exist. Creating...');

    const defaultJson = { counter: 0 };

    // Create the data directory if it doesn't exist
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir);
    }

    fs.writeFileSync(filePath, JSON.stringify(defaultJson));
    console.log('File created with default value:', defaultJson);
  }
}

checkOrCreateJSONFile();

app.use("/", endpoints)

app.use(apiErrorHandler);

app.listen(port, host, () => {
    console.log(`Example app listening at http://${host}:${port}`)
})

//module.exports = app
