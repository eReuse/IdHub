const axios = require("axios")
const api_url = "http://api_connector:3010"
const ADMIN_TOKEN = process.env.ADMIN_TOKEN
const OPERATOR_TOKEN = process.env.OPERATOR_TOKEN
var route = "mintTokens"
var params= {
    Address:"0x9689c31ddc9fD8F0Fcb98B7570E82893d9a7E593",
    api_token: ADMIN_TOKEN 
}

const dlt = "ethereum"
axios.post(`${api_url}/${route}`, params, {
    headers: {
        dlt: dlt
    }
}).then(data => {
    route="allowTokens"
    params = {
        Amount:10000,
        api_token: OPERATOR_TOKEN 
    }
    axios.post(`${api_url}/${route}`, params, {
        headers: {
            dlt: dlt
        }
    }).then(response => {
        // TODO less logs
        console.error(response.data)
    })
}
    
)
