function search() {
    dpp = document.getElementById('dpp').value
    chid = dpp.split(":")[0]
    var url = `http://45.150.187.47:3011/did:ereuse:${chid}`
    axios.get(url)
        .then(data => {
            console.log(data)
            let service
            if (data.data.didDocument == null)
                document.getElementById('res').innerHTML = "NOT FOUND"
            else {


                data.data.didDocument.service.forEach(element => {
                    if (element.type == "DeviceHub")
                        service = element
                });
                url = `http://localhost:3012/getURL?id=${service.serviceEndpoint}`
                axios.get(url)
                    .then(response => {
                        console.log(response)
                        htmlText = `DeviceHub link for ${dpp}:<br>
            <a href="http://${response.data.url + "/dids/" + dpp}">${response.data.url + "/dids/" + dpp}</a>`
                        document.getElementById('res').innerHTML = htmlText
                    })
            }

        })
        .catch(err => console.log(err))
}