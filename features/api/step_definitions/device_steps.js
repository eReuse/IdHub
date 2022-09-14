const { Given, When, Then, Before, BeforeAll } = require('@cucumber/cucumber');
const testhelper = require('../testing_helper')

Given('a new unique CHID', function (){
    this.params["DeviceCHID"] = Math.floor(Math.random() * 9999)
})