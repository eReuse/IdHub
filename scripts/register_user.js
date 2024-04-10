// payload = {
//     'privateKey' : privateKey
// }
// res = requests.post(endpoint + "/registerUser", data=payload)
// return res.json()

const axios = require("axios")
const api_url = "http://localhost:3010"
const route = "registerUser"
const params= {
    privateKey:"b1a456156a846f256783b90af3da3317f05297909ba56be6faed916f1f281611"
}

const dlt = "ethereum"
axios.post(`${api_url}/${route}`, params, {
    headers: {
        dlt: dlt
    }
}).then(data => {
    console.log(data)
}
    
)