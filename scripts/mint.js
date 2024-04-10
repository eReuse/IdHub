const axios = require("axios")
const api_url = "http://localhost:3010"
var route = "mintTokens"
var params= {
    Address:"0x9689c31ddc9fD8F0Fcb98B7570E82893d9a7E593",
    api_token: "jiNQMB6MYc4NUs0.cxyKF6Qd7qsGLATBWVMEkFGmguaDRXPuta0neJlIBgUw7UwZLMALmuW9Qhd3pE7d"
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
        api_token: "EQlh9Iqwj8xDVHg.KrsIRTQ38k4q3lItg8NlybTK7QSvsL6BOO7Cm3upghobI2Y4Q7PlsjWwUEq0ByGh"
    }
    axios.post(`${api_url}/${route}`, params, {
        headers: {
            dlt: dlt
        }
    }).then(dat => {
        console.log(dat)
    })
}
    
)