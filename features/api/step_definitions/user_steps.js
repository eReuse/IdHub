const { Given, When, Then, Before } = require('@cucumber/cucumber');
const assert = require('assert').strict
const ethers = require("ethers")

Given('a user with a randomly generated ethereum privkey', function() {
    //first two characters "Ox" are deleted 
    this.params = {
        privateKey: ethers.Wallet.createRandom().privateKey.slice(2)
    }
})

Given('a user with an invalid ethereum privkey', function() {
    //first two characters "Ox" are deleted + 1 character to make it invalid
    this.params = {
        privateKey: ethers.Wallet.createRandom().privateKey.slice(3)
    }
})

Then('the deleted token', function () {
    assert.equal(this.response.data.data.deleted_token, this.params.api_token)
});

Then('a valid api_token, ethereum_keypar and iota_id', function () {
    assert(this.response.data.data.api_token!=undefined)
    assert(this.response.data.data.eth_priv_key!=undefined)
    assert(this.response.data.data.eth_pub_key!=undefined)
    assert(this.response.data.data.iota_id!=undefined)
});

Then('a valid api_token, the given ethereum_keypar and iota_id', function () {
    assert(this.response.data.data.api_token!=undefined)
    //console.log("privkeyreturn: ",this.response.data.data.eth_priv_key.slice(2))
    //console.log("privkeysteps: ",this.params.privateKey)
    assert(this.response.data.data.eth_priv_key.slice(2)==this.params.privateKey)
    assert(this.response.data.data.eth_pub_key!=undefined)
    assert(this.response.data.data.iota_id!=undefined)
});
