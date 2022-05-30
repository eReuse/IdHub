const { IdentityClient, CredentialTypes, UserType, IdentityJson, ChannelClient, AccessRights } =require('@iota/is-client');
const { DppClient, toDppIdentity } = require('@iota/is-ict-dpp');
const { defaultConfig } = require('./iota-config');
const storage = require('node-persist');
const {readFileSync} = require('fs');

const relPath = process.cwd() + "/../utils/iota/";
const identity_file = "./adminIdentity.json"
const identity_path = relPath + identity_file;
const managerIdentityJSON= JSON.parse(readFileSync(identity_path).toString());
const managerIdentity = toDppIdentity(managerIdentityJSON)

const dppClient = new DppClient(defaultConfig);
const deviceService = dppClient.devices();
const identityService = dppClient.identities();
const eventService = dppClient.events();

const identityClient = new IdentityClient(defaultConfig);


function get_timestamp(){
    return parseInt((new Date().getTime() / 1000).toFixed(0))
}

async function create_identity() {
    const username = 'eReuse-test-user-' + Math.ceil(Math.random() * 100000);
    console.log("Creating user identity...")
    const userIdentity = await identityClient.create(username);
    console.log("User identity created.")
    return userIdentity;
}

async function create_device_channel(userIdentity, chid) {
    await storage.init()
    const index_channel = await storage.getItem("iota-index-channel")
    var timestamp = get_timestamp()
    const { channelAddress, verifiableCredential } = await deviceService.registerDevice({
        managerIdentity: managerIdentity,
        ownerIdentity: toDppIdentity(userIdentity),
        credentialType: dppClient.getOwnershipCredentialType(),
        indexChannelAddress: index_channel.channelAddress,
        type: 'proof_of_register',
        chId: chid,
        payload: { chid:chid, timestamp: timestamp },
    });

    return { channelAddress, verifiableCredential, timestamp }
}

async function create_index_channel(channelName) {
    const channelClient = new ChannelClient(defaultConfig);
    await channelClient.authenticate(managerIdentity.did, managerIdentity.secretKey);

    console.log("Creating index channel...")
    const logChannel = await channelClient.create({
        name: channelName,
        topics: [{ type: 'eReuse-index', source: 'eReuse' }]
    });
    console.log("Index channel created.")

    return logChannel
}

async function write_device_channel(userIdentity, credential, chid, type, payload) {
    let owner_mode = false
    if (credential.credentialSubject?.role == undefined) owner_mode = true
    const channelAddress = await lookup_device_channel(chid)

    payload.timestamp = get_timestamp()

    console.log("Writing proof to device channel...")
    if (owner_mode){
        await eventService.writeOnChannel({
            channelAddress: channelAddress,
            payload: payload,
            subjectIdentity: toDppIdentity(userIdentity),
            credential: credential,
            type: type
        })
    }
    else {
        await eventService.oneShotWrite({
            managerIdentity: managerIdentity,
            subjectIdentity: toDppIdentity(userIdentity),
            payload: payload,
            channelAddress: channelAddress,
            credential: credential,
            type: type
        })
    }
    console.log("Proof written.")

    return payload.timestamp
}

async function read_device_channel(userIdentity, credential, chid) {
    let owner_mode = false
    if (credential.credentialSubject?.role == undefined) owner_mode = true

    const channelAddress = await lookup_device_channel(chid)
    let channelData;

    console.log("Reading device channel data...")
    if(owner_mode){
        channelData = await eventService.readDeviceChannel(channelAddress, toDppIdentity(userIdentity))
    }
    else{
        channelData = await eventService.auditDeviceChannel({
            managerIdentity: managerIdentity,
            channelAddress: channelAddress,
            credential: credential
        })
    }
    console.log("Data read.")
    return channelData
}

async function read_device_proofs_of_issue(userIdentity, credential, chid) {
    var channelData = await read_device_channel(userIdentity, credential, chid)
    var response = []
    var deregister_timestamp = undefined;

    for (var i = 0; i < channelData.length; i+=1) {
        if (channelData[i].log.type == "proof_of_deregister") {
            deregister_timestamp = channelData[i].log.payload.timestamp
            console.log("DEREGISTER TIMESTAMP: " + deregister_timestamp)
            i = channelData.length;
        }
    }

    //next if prob doable prettier
    if (deregister_timestamp != undefined) {
        channelData.forEach((data) => {
            if (data.log.type == "proof_of_issue" && data.log.payload.timestamp < deregister_timestamp)
                response.push(data.log.payload)
        })
    }
    else {
        channelData.forEach((data) => {
            if (data.log.type == "proof_of_issue")
                response.push(data.log.payload)
        })
    }

    return response
}

async function read_device_generic_proofs(userIdentity, credential, chid) {
    var channelData = await read_device_channel(userIdentity, credential, chid)
    var response = []

    channelData.forEach((data) => {
        if (data.log.type == "generic_proof")
            response.push(data.log.payload)
    })

    return response
}

async function read_device_proofs_of_register(userIdentity, credential, chid) {
    var channelData = await read_device_channel(userIdentity, credential, chid)
    var response = []

    channelData.forEach((data) => {
        if (data.log.type == "proof_of_register") {
            let proof_data = {
                timestamp: data.log.payload.timestamp
            }
            response.push(proof_data)
        }
    })

    return response
}

async function read_device_deregister_proof(userIdentity, credential, chid) {
    var channelData = await read_device_channel(userIdentity, credential, chid)
    var response = undefined;
    
    for (var i = 0; i < channelData.length; i+=1) {
        if (channelData[i].log.type == "proof_of_deregister") {
            console.log("PROOF OF DEREGISTER FOUND. TIMESTAMP:")
            console.log(channelData[i].log.payload.timestamp)
            response = channelData[i].log.payload.timestamp
            i = channelData.length;
        }
    }
    return response
}

async function lookup_device_channel(chid) {
    console.log("Looking up device address in index channel...")
    await storage.init()
    const index_channel = await storage.getItem("iota-index-channel")

    try{
        const deviceChannelAddress = await eventService.lookUpDeviceChannel(chid, index_channel.channelAddress, managerIdentity)
        return deviceChannelAddress
    } catch(e){
        return false
    }
    
}

async function issue_credential(userIdentity, role){
    const credential = await identityService.createCredential(
        managerIdentity,
        userIdentity.doc.id,
        dppClient.getOwnershipCredentialType(),
        {
            role: role
        }
    )

    return credential
}

async function get_iota_id(token) {
    var split_token = token.split(".");
    const item = await storage.getItem(split_token[0]);

    //skip check for undefined as this should only be called after checking the token validity
    return item.iota_id
}

async function get_credential(token, type, chid=undefined) {
    var split_token = token.split(".");
    const item = await storage.getItem(split_token[0]);

    if(type != "ownership") return item.iota.credentials[type]
    else return item.iota.credentials[type][chid]
    
}

async function check_iota_index() {
    await storage.init()
    try {
        if (await storage.getItem("iota-index-channel") == undefined) {
            let channel = await create_index_channel('eReuse-test-index-' + Math.ceil(Math.random() * 100000))
            await storage.setItem("iota-index-channel", channel)
        }
    } catch (e) {
        console.log(e)
        console.log("WARNING: Couldn't create iota index channel!")
    }
}

module.exports = {
    create_identity,
    create_index_channel,
    create_device_channel,
    read_device_proofs_of_issue,
    read_device_generic_proofs,
    read_device_proofs_of_register,
    read_device_deregister_proof,
    write_device_channel,
    lookup_device_channel,
    check_iota_index,
    get_iota_id,
    get_credential,
    issue_credential
}