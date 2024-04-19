// payload = {
//     'privateKey' : privateKey
// }
// res = requests.post(endpoint + "/registerUser", data=payload)
// return res.json()

const axios = require("axios")
const api_url = "http://localhost:3010"
const route = "registerUser"
const params= {
    privateKey:"1499c33a69d24593a3e1304852ea1749e8ffad8886c7641b14a7b5635967fb06"
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