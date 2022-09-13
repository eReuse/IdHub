const { Given, When, Then, Before, BeforeAll } = require('@cucumber/cucumber');
const testhelper = require('../testing_helper')
const fs = require('fs')
const assert = require('assert').strict


Given('a valid API user with an issuer credential', async function (){
    try {
        var jsonAdmin = fs.readFileSync('./features/api/adminToken.json')
        this.response = await testhelper.make_post("registerUser", this.params, "ethereum")
        this.api_token_issuer = this.response.data.data.api_token
        this.target_user = this.response.data.data.api_token.substring(0,15)

        this.params["api_token"] = JSON.parse(jsonAdmin).admin_token;
        this.params["target_user"] = this.target_user

        this.response = await testhelper.make_post("setIssuer", this.params, "ethereum")
        this.params["api_token"] = this.api_token_issuer
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
})

When('issuer user sends a Post request to the path {string} with {string} credential to the target user', async function (string, string2) {
    try {
        this.params["CredentialType"] = string2
        this.params["target_user"] = this.target_user
        this.response = await testhelper.make_post(string, this.params, "ethereum")
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
});

Then('a get resquest to {string} of the target user returns true in the {string} camp', async function (string, string2) {
    try {
        this.params["api_token"] = this.target_user_full
        this.response = await testhelper.make_post(string, this.params, "ethereum")

    } catch (err) {
        console.log(err)
        this.response = err.response
    }
    //TODO use string2 to get to the desired response object
    if (string2 == "isOperator") assert.equal(this.response.data.data.isOperator, true)
    else if (string2 == "isWitness") assert.equal(this.response.data.data.isWitness, true)
    else if (string2 == "isVerifier") assert.equal(this.response.data.data.isVerifier, true) 
        
});

