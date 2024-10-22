const express = require("express")
var router = express.Router();
const fs = require('fs');
const ApiError = require('./utils/apiError')

var filePath = "../data/id_url.json"


router

.get('/getURL', (req, res, next) => {
    var id = req.query.id
    try {
        const fileData = fs.readFileSync(filePath, 'utf8');
        const jsonData = JSON.parse(fileData);
        if(jsonData[id] == undefined){
            next(ApiError.badRequest('ID doesnt exist'));
            return
        }
        res.header("Access-Control-Allow-Origin", "*");
        res.status(200);
        res.json({
            url: jsonData[id]
        })
    } catch (error){
        console.error('Error:', error);
    }
})

.get('/getAll', (req, res, next) => {
    try {
        const fileData = fs.readFileSync(filePath, 'utf8');
        const jsonData = JSON.parse(fileData);
        res.status(200);
        res.json({
            url: jsonData
        })
    } catch (error){
        console.error('Error:', error);
    }
})

.post("/registerURL", (req, res, next) => {
    var new_url = req.body.url
    console.log(new_url)
    try {
        if(new_url == undefined){
            next(ApiError.badRequest('url param not found'));
            return
        }
        // Read the file contents
        const fileData = fs.readFileSync(filePath, 'utf8');
      
        // Parse the JSON data
        const jsonData = JSON.parse(fileData);
      
        // Use the JSON data
        jsonData.counter++
        const new_id = `DH${jsonData.counter}`
        jsonData[new_id] = new_url

        fs.writeFileSync(filePath, JSON.stringify(jsonData));

        res.status(201);
        res.json({
            id: new_id
        })
      } catch (error) {
        console.error('Error:', error);
      }
})

module.exports = router