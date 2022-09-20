const { Given, When, Then, Before, BeforeAll } = require('@cucumber/cucumber');
const testhelper = require('../testing_helper')
const assert = require('assert').strict


Given('a new unique CHID', function (){
    this.params["DeviceCHID"] = Math.floor(Math.random() * 9999).toString()
})

Given('an empty CHID', function (){
    this.params["DeviceCHID"] = undefined
})

Given('The Operator registers a device with a new unique CHID', async function (){
    try {
        this.params["DeviceCHID"] = Math.floor(Math.random() * 9999).toString()
        this.response = await testhelper.make_post("registerDevice", this.params, "ethereum")
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
    //this.params["DeviceCHID"] = Math.floor(Math.random() * 9999).toString()
})

When('sends a Post request to the path {string} with the same CHID', async function (string) {
    try {
        this.response = await testhelper.make_post(string, this.params, "ethereum")
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
});

Then('the registered device address on ethereum', function (){
    assert(this.response.data.data.deviceAddress!=undefined)
})