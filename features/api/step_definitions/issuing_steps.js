const { Given, When, Then, Before } = require('@cucumber/cucumber');
const cucumber = require('@cucumber/cucumber')
const assert = require('assert').strict
const axios = require('axios')
const fs = require('fs')

//const api_url = 'http://dlt.example.com:3005';
const api_url = 'http://localhost:3010';
cucumber
Given('an admin token and a target user', async function () {
    //generate user
    try {
        this.response = await make_post("registerUser", this.params)
        this.target_user = this.response.data.data.api_token.substring(0,15)
    } catch (err) {
        this.response = err.response
    }
    var jsonAdmin = fs.readFileSync('./features/api/adminToken.json')
    this.params = {
        target_user: this.target_user,
        api_token: JSON.parse(jsonAdmin).admin_token
    }
})

When('sends a Post request to the path {string} with target user token and admin token', async function(string){
    try {
        this.response = await make_post(string, this.params)
    } catch (err) {
        this.response = err.response
    }
})

async function make_post(route, params) {
    try {
        return await axios.post(`${api_url}/${route}`, params, {
            headers: {
                dlt: "ethereum"
            }
        })
    }
    catch (err) {
        return err
    }
}
