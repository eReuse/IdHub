const { Given, When, Then, Before, BeforeAll } = require('@cucumber/cucumber');
const testhelper = require('../testing_helper')
const fs = require('fs')

Before(function () {
    //initialize params object to be able to dinamically add new elements to it
    //in each step of each scenario
    //https://stackoverflow.com/questions/44983567/how-to-assign-add-value-to-a-undefined-item-in-a-json-object
    this.params = {}
});

Given('an API admin user', async function () {
    var jsonAdmin = fs.readFileSync('./features/api/adminToken.json')
    this.params["api_token"] = JSON.parse(jsonAdmin).admin_token;
})

Given('a valid API user', async function (){
    try {
        this.response = await testhelper.make_post("registerUser", this.params, "ethereum")
        this.api_token = this.response.data.data.api_token
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
    this.params["api_token"] = this.api_token
})

Given ('an invalid API user', async function (){
    try {
        this.response = await testhelper.make_post("registerUser", this.params, "ethereum")
        this.api_token = testhelper.invalidate_string(this.response.data.data.api_token)
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
    this.params["api_token"] = this.api_token
})

Given ('a valid target user', async function (){
    try {
        this.response = await testhelper.make_post("registerUser", this.params, "ethereum")
        this.target_user = this.response.data.data.api_token.substring(0,15)
        this.target_user_full = this.response.data.data.api_token
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
    this.params["target_user"] = this.target_user
})

Given ('an invalid target user', async function (){
    try {
        this.response = await testhelper.make_post("registerUser", this.params, "ethereum")
        this.target_user = testhelper.invalidate_string(this.response.data.data.api_token.substring(0,15))
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
    this.params["target_user"] = this.target_user
})

When('sends a Post request to the path {string} with the given parameters', async function (string) {
    try {
        this.response = await testhelper.make_post(string, this.params, "ethereum")
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
});

When('sends a Post request to the path {string} without parameters', async function (string) {
    try {
        this.response = await testhelper.make_post(string, this.params, "ethereum")
    } catch (err) {
        console.log(err)
        this.response = err.response
    }
});