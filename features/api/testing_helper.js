const axios = require('axios')

const api_url = 'http://localhost:3010';

var {setDefaultTimeout} = require('@cucumber/cucumber');
setDefaultTimeout(30 * 1000);

function invalidate_string(string) {
    return string.substring(1)
}

async function make_post(route, params, dlt) {
    try {
        return await axios.post(`${api_url}/${route}`, params, {
            headers: {
                dlt: dlt
            }
        })
    }
    catch (err) {
        return err
    }
}

module.exports = {
    invalidate_string,
    make_post
}