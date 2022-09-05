const { Given, When, Then, Before } = require('@cucumber/cucumber');
const assert = require('assert').strict
const axios = require('axios')
//const api_url = 'http://dlt.example.com:3005';
const api_url = 'http://localhost:3010';

const privateKey = undefined;
let response;

When('sends a Post request to the path {string} without ethereum keypar', async function (string) {
    try {
        this.response = await make_post(string, privateKey)

    } catch (err) {
        this.response = err.response
    }
});

Then ('gets a response with code {int}', function(int) {
    assert.equal(this.response.status, 200)
    console.log("response esperada 201: ", this.response.status)
    return response
});

Then('status {string}', function (string) {
    assert.equal(this.response.data.status, string)
});

async function make_post(route, privateKey) {
    try {
        return await axios.post(`${api_url}/${route}`, privateKey, {
            headers: {
                dlt: "ethereum"
            }
        })
    }
    catch (err) {
        return err
    }
}
