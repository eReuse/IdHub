const { Given, When, Then, Before, BeforeAll } = require('@cucumber/cucumber');
const testhelper = require('../testing_helper')
const assert = require('assert').strict

var usedCHIDs = []

function generateUniqueCHID() {
    var found = false;
    var newCHID;
    while (found == false) {
        newCHID = Math.floor(Math.random() * 9999999).toString()
        if (!usedCHIDs.includes(newCHID)) {
            usedCHIDs.push(newCHID)
            found = true;
            //console.log(newCHID)
        }
        // else {
        //     console.log("retry random CHID" + " was " + newCHID)
        // }
    }
    return newCHID
}


Given('a new unique CHID', function (){
    this.params["DeviceCHID"] = generateUniqueCHID()
    // this.params["DeviceCHID"] = Math.floor(Math.random() * 9999).toString()
    // usedCHIDs.push(this.params["DeviceCHID"])
    // console.log(usedCHIDs)
})

Given('an empty CHID', function (){
    this.params["DeviceCHID"] = undefined
})

Given('a correct DPP that contains an existent CHID', function (){
    const halfDPP = Math.floor(Math.random() * 9999).toString()
    this.params["DeviceDPP"] = this.params["DeviceCHID"] + ":" + halfDPP
})

Given('a correct DPP that does not contain an existent CHID', function (){
    const halfDPP = Math.floor(Math.random() * 9999).toString()
    this.params["DeviceDPP"] = halfDPP + ":" + halfDPP
})


Given('an incorrect DPP', function (){
    const halfDPP = Math.floor(Math.random() * 9999).toString()
    this.params["DeviceDPP"] = this.params["DeviceCHID"] + halfDPP
})

Given('a DocumentID, DocumentSignature, IssuerID', function (){
    this.params["DocumentID"] = "Test Document " + Math.floor(Math.random() * 9999).toString()
    this.params["DocumentSignature"] = "Test Document signature " + Math.floor(Math.random() * 9999).toString()
    this.params["IssuerID"] = "Test IssuerID " + Math.floor(Math.random() * 9999).toString()

})

Given('The Operator registers a device with a new unique CHID', async function (){
    try {
        this.params["DeviceCHID"] = generateUniqueCHID()
        this.response = await testhelper.make_post("registerDevice", this.params, "ethereum")
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
    //this.params["DeviceCHID"] = Math.floor(Math.random() * 9999).toString()
})

When('{string} sends a Post request to the path {string} with the same CHID', async function (string, string2) {
    try {
        this.response = await testhelper.make_post(string2, this.params, "ethereum")
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
});

Then('the registered device address on ethereum', function (){
    assert(this.response.data.data.deviceAddress!=undefined)
})