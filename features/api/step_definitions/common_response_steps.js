const { Given, When, Then, Before } = require('@cucumber/cucumber');
const assert = require('assert').strict


Then ('gets a response with code {int}', function(int) {
    assert.equal(this.response.status, int)
});

Then ('gets an error response with code {int}', function(int) {
    assert.equal(this.response.response.status, int)
});

Then ('response error message {string}', function(string) {
    assert.equal(this.response.response.data, string)
});

Then('status {string}', function (string) {
    assert.equal(this.response.data.status, string)
});