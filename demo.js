const rl = require("readline-sync");
// const rl = readline.createInterface({
//     input: process.stdin,
//     output: process.stdout
// });
const { SHA3 } = require('sha3');
const axios = require('axios')
var api_url
var dlt
//const abc3_api= "http://10.1.1.24:3005"
const localhost_3005= "http://127.0.0.1:3005"
const localhost_3010= "http://127.0.0.1:3010"
const ereuse_api_3005= "http://dlt.example.com:3005"
const ereuse_api_3010= "http://dlt.example.com:3010"


function print_post_result(res, read){
    console.clear()
    //console.log("ERROR:  " + res + "\n\n\n");
    if(res.data == undefined) console.log(res.response.data.data);
    else {
        console.log("")
        if (!read)
            console.log(res.data)
        else
            console.log(res.data.data)
        console.log("")
    }
}

async function make_post(route,params){
    try{
        return await axios.post(`${api_url}/${route}`, params, {
            headers: {
                 dlt: dlt
                }
            })
    }
    catch(err){
        return err
    }
}

async function make_get(route){
    return await axios.get(`${api_url}/${route}`)
}

async function getUserDeployedDevices(){
    const res = await make_get("getDeployedDevices")
    print_post_result(res, true)
}
async function getAllDeployedDevices(){
    const res = await make_get("getAllDeployedDevices")
    print_post_result(res, true)
}

async function register_device(){
    params = {
        DeviceCHID: rl.question("Device CHID: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("registerDevice",params)
    print_post_result(res,false)
}

async function deRegisterDevice(){
    params = {
        DeviceCHID: rl.question("Device CHID: "),
        CredentialType: rl.question("Credential type: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("deRegisterDevice",params)
    print_post_result(res,false)
}

async function generateProof(){
    params = {
        DeviceCHID: rl.question("Device CHID: "),
        IssuerID: rl.question("Issuer ID: "),
        DocumentID: rl.question("Document ID: "),
        DocumentSignature: rl.question("Document signature: "),
        Type: rl.question("Document type: "),
        CredentialType: rl.question("Credential type: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("generateProof",params)
    print_post_result(res,false)
}

async function transferDevice(){
    params = {
        to: rl.question("To: "),
        new_registrant: rl.question("New registrant: "),
        device_address: rl.question("Device address: ")
    }
    const res = await make_post("transfer",params)
    print_post_result(res,false)
}

async function recycleDevice(){
    params = {
        device_address: rl.question("Device address: ")
    }
    const res = await make_post("recycle",params)
    print_post_result(res,false)
}

async function getDeviceData(){
    params = {
        device_address: rl.question("Device address: ")
    }
    const res = await make_post("getData",params)
    print_post_result(res,true)
}

async function getTrasferProofs(){
    params = {
        device_address: rl.question("Device address: ")
    }
    const res = await make_post("getTransferProofs",params)
    //console.log(res)
    print_post_result(res,true)
}

async function getRecycleProofs(){
    params = {
        device_address: rl.question("Device address: ")
    }
    const res = await make_post("getRecycleProofs",params)
    print_post_result(res,true)
}

async function getProofs(){
    params = {
        DeviceCHID: rl.question("Device CHID: "),
        CredentialType: rl.question("Credential type: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("getProofs",params)
    print_post_result(res,true)
}

async function getIssueProofs(){
    params = {
        DeviceCHID: rl.question("Device CHID: "),
        CredentialType: rl.question("Credential type: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("getIssueProofs",params)
    print_post_result(res,true)
}

async function getRegisterProofsByCHID(){
    params = {
        DeviceCHID: rl.question("Device CHID: "),
        CredentialType: rl.question("Credential type: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("getRegisterProofsByCHID",params)
    print_post_result(res,true)
}

async function getDeRegisterProofs(){
    params = {
        DeviceCHID: rl.question("Device CHID: "),
        CredentialType: rl.question("Credential type: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("getDeRegisterProofs",params)
    print_post_result(res,true)
}


async function createStamp(){
    const hash = new SHA3(256);
    hash.update(rl.question("Hash: "))
    params = {
        hash: hash.digest('hex')
    }
    const res = await make_post("createStamp",params)
    print_post_result(res,false)
}

async function checkStamp(){
    const hash = new SHA3(256);
    hash.update(rl.question("Hash: "))
    params = {
        hash: hash.digest('hex')
    }
    const res = await make_post("checkStamp",params)
    print_post_result(res,true)
}

async function translate(){
    params = {
        DeviceCHID: rl.question("Device CHID: ")
    }
    const res = await make_post("translate",params)
    print_post_result(res,true)
}

async function issuePassport(){
    params = {
        DeviceDPP: rl.question("Device DPP: "),
        DocumentID: rl.question("Document ID: "),
        DocumentSignature: rl.question("Document signature: "),
        IssuerID: rl.question("IssuerID: "), 
        CredentialType: rl.question("Credential type: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("issuePassport",params)
    print_post_result(res,false)
}

async function registerUser(){
    params = {
        privateKey: rl.question("privateKey: "),
    }
    const res = await make_post("registerUser",params)
    print_post_result(res,false)
}

async function invalidateUser(){
    params = {
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("invalidateUser",params)
    print_post_result(res,false)
}

async function setIssuer(){
    params = {
        target_user: rl.question("Target user: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("setIssuer",params)
    print_post_result(res,false)
}

async function issueCredential(){
    params = {
        CredentialType: rl.question("Credential type: "),
        target_user: rl.question("Target user: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("issueCredential",params)
    print_post_result(res,false)
}

async function transferDevice(){
    params = {
        DeviceCHID: rl.question("Device to transfer: "),
        NewOwner: rl.question("New owner: "),
        api_token: rl.question("api_token: "),
    }
    const res = await make_post("transferOwnership",params)
    print_post_result(res,false)
}

function menu(){
    return "[1] Register device.\n"+
    "[2] Issue a new passport.\n"+
    "[3] Generate proof.\n"+
    "[4] Get proof.\n"+
    "[5] Get Issue proof.\n"+
    "[6] Get register proof.\n"+
    "[7] DeRegister device.\n"+
    "[8] Get deRegister proof.\n"+
    "[9] Register new user.\n"+
    "[a] Invalidate user.\n" +
    "[b] Set issuer credential.\n" +
    "[c] Issue credential.\n" +
    "[d] Transfer device.\n" +
    "\nChoose an option:" 
    
}

async function main(){
    var select = rl.question(
    "[1] localhost:3005\n"+
    "[2] localhost:3010\n"+
    "[3] ereuse:3005\n"+
    "[4] ereuse:3010\n"+
    "\nSelect endpoint: ")
    if (select == 1) api_url=localhost_3005
    else if(select == 2) api_url = localhost_3010
    else if (select == 3) api_url = ereuse_api_3005
    else api_url = ereuse_api_3010
    console.clear()

    var selectDLT = rl.question(
    "[1] EREUSE Ethereum\n"+
    "[2] IOTA\n"+
    "\nSelect DLT: ")
    if (selectDLT == 1) dlt = "ethereum"
    else if(selectDLT == 2) dlt = "iota"    
    
    console.clear()
    var option;
    while(true){
        option = rl.question(menu());
        switch (option) {
            case '0': rl.close()
            case '1':
                await register_device()
                break;
            case '2':
                await issuePassport()
                break;
            case '3':
                await generateProof()
                break;
            case '4':
                await getProofs()
                break;
            case '5':
                await getIssueProofs()
                break;
            case '6':
                await getRegisterProofsByCHID()
                break;
            case '7':
                await deRegisterDevice()
                break;
            case '8':
                await getDeRegisterProofs()
                break;
            case '9':
                await registerUser()
                break;
            case 'a':
                await invalidateUser()
                break;
            case 'b':
                await setIssuer()
                break;
            case 'c':
                await issueCredential()
                break;
            case 'd':
                await transferDevice()
                break;
        }
    }  
}
main()


