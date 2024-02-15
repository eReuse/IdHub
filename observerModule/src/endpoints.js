const express = require("express")
var router = express.Router();
const fs = require('fs');
const ApiError = require('./utils/apiError')
const Fuse = require('fuse.js')

var filePath = "../data/devices.json"
const fuseOptions = {
	// isCaseSensitive: false,
	includeScore: true,
	// shouldSort: true,
	includeMatches: true,
	// findAllMatches: false,
	// minMatchCharLength: 1,
	// location: 0,
	threshold: 0.4,
	// distance: 100,
	// useExtendedSearch: false,
	// ignoreLocation: false,
	// ignoreFieldNorm: false,
	// fieldNormWeight: 1,
	keys: [
		"chassis",
        "manufacturer",
        "model",
        "serialNumber",
        "sku",
        "type",
        "version",
        "system_uuid",
        "family",
        "chid",
        "phid"
	]
};

router

.get('/search', (req, res, next) => {
    var query = req.query.query
    try {
        const fileData = fs.readFileSync(filePath, 'utf8');
        const jsonData = JSON.parse(fileData);
        const fuse = new Fuse(jsonData, fuseOptions);
        const searchPattern = query
        const result = fuse.search(searchPattern)
        res.header("Access-Control-Allow-Origin", "*");
        res.status(200);
        res.json({
            result
        })
    } catch (error){
        console.error('Error:', error);
    }
})

module.exports = router