const { IdentityClient, CredentialTypes, UserType, IdentityJson, ChannelClient, AccessRights } =require('@iota/is-client');
const { defaultConfig } = require('./configuration-iota');
const storage = require('node-persist');
const {readFileSync} = require('fs');

const identity_file= "./adminIdentity.json"

async function create_identity() {
    const identityClient = new IdentityClient(defaultConfig);
    const username = 'eReuse-test-user-' + Math.ceil(Math.random() * 100000);
    console.log("Creating user identity...")
    const userIdentity = await identityClient.create(username);
    console.log("User identity created.")
    return userIdentity;
}

async function create_device_channel(userIdentity, chid) {
    const channelClient = new ChannelClient(defaultConfig);
    const channelClientUser = new ChannelClient(defaultConfig);
    const ereuseIdentity = JSON.parse(readFileSync(identity_file).toString());
    await channelClient.authenticate(ereuseIdentity.doc.id, ereuseIdentity.key.secret);
    await channelClientUser.authenticate(userIdentity.doc.id, userIdentity.key.secret);
  
    console.log("Creating device channel...")
    const logChannel = await channelClient.create({
      name: chid,
      topics: [{ type: 'eReuse-device', source: chid }]
    });
    console.log("Channel created with address: "+logChannel.channelAddress)

    console.log("Requesting access...")
    await channelClientUser.requestSubscription(logChannel.channelAddress, {
        accessRights: AccessRights.ReadAndWrite
    });

    console.log("Granting access...")
    await channelClient.authorizeSubscription(logChannel.channelAddress, {
        id: userIdentity.doc.id
    });

    console.log("Access granted.")

    var timestamp = parseInt((new Date().getTime() / 1000).toFixed(0))

    console.log("Writing proof of register...")
    await channelClientUser.write(logChannel.channelAddress,{
        type: 'proof_of_register',
        created: new Date().toISOString(),
        payload: {chid: chid, timestamp:timestamp}
    })
    console.log("Proof of register written.")

    await write_index_channel(chid, channelClient, logChannel.channelAddress)

    let retChannel = logChannel.channelAddress
  
    return {retChannel, timestamp}
}

async function create_index_channel(channelName) {
    const channelClient = new ChannelClient(defaultConfig);
    const ereuseIdentity = JSON.parse(readFileSync(identity_file).toString());
    await channelClient.authenticate(ereuseIdentity.doc.id, ereuseIdentity.key.secret);
  
    console.log("Creating index channel...")
    const logChannel = await channelClient.create({
      name: channelName,
      topics: [{ type: 'eReuse-index', source: 'eReuse' }]
    });
    console.log("Index channel created.")
  
    return logChannel
}

async function write_device_channel(userIdentity, chid, type, payload){
    const channelClient = new ChannelClient(defaultConfig);
    await channelClient.authenticate(userIdentity.doc.id, userIdentity.key.secret);

    const channelAddress = await lookup_device_channel(chid)

    payload.timestamp=parseInt((new Date().getTime() / 1000).toFixed(0))

    console.log("Writing proof to device channel...")
    await channelClient.write(channelAddress,{
        type: type,
        created: new Date().toISOString(),
        payload: payload
    })
    console.log("Proof written.")

    return payload.timestamp
}

async function write_index_channel(chid, channelClient, deviceChannel){
    console.log("Writing index to index channel...")
    await storage.init()
    const index_channel = await storage.getItem("iota-index-channel")
    const channelAddress = index_channel.channelAddress
    await channelClient.write(channelAddress,{
        type: "index",
        created: new Date().toISOString(),
        payload: {chid:chid, channelAddress:deviceChannel}
    })
    console.log("Index written.")
}

async function read_device_channel(userIdentity, chid){
    const channelClient = new ChannelClient(defaultConfig);
    await channelClient.authenticate(userIdentity.doc.id, userIdentity.key.secret);

    const channelAddress = await lookup_device_channel(chid)

    console.log("Reading device channel data...")
    const channelData = await channelClient.read(channelAddress);
    console.log("Data read.")
    return channelData
}

async function read_device_proofs_of_issue(userIdentity, chid){
    var channelData = await read_device_channel(userIdentity, chid)
    var response = []

    channelData.forEach((data) => {
        if(data.log.type == "proof_of_issue")
            response.push(data.log.payload)
    })

    return response
}

async function read_device_generic_proofs(userIdentity, chid){
    var channelData = await read_device_channel(userIdentity, chid)
    var response = []

    channelData.forEach((data) => {
        if(data.log.type == "generic_proof")
            response.push(data.log.payload)
    })

    return response
}

async function read_device_proofs_of_register(userIdentity, chid){
    var channelData = await read_device_channel(userIdentity, chid)
    var response = []

    channelData.forEach((data) => {
        if(data.log.type == "proof_of_register"){
            let proof_data = {
                timestamp: data.log.payload.timestamp
            }
            response.push(proof_data)
        } 
    })

    return response
}

async function lookup_device_channel(chid){
    const channelClient = new ChannelClient(defaultConfig);
    const ereuseIdentity = JSON.parse(readFileSync(identity_file).toString());
    await channelClient.authenticate(ereuseIdentity.doc.id, ereuseIdentity.key.secret);

    console.log("Looking up device address in index channel...")
    await storage.init()
    const index_channel = await storage.getItem("iota-index-channel")
    const channelAddress = index_channel.channelAddress
    const channelData = await channelClient.read(channelAddress);
    for(let i=0; i< channelData.length; ++i){
        if(channelData[i].log.payload.chid == chid){
            console.log("Device found.")
            return channelData[i].log.payload.channelAddress
        }
    }
    console.log("Device not found.")

    return false
}

module.exports={create_identity, 
    create_index_channel, 
    create_device_channel, 
    read_device_proofs_of_issue, 
    read_device_generic_proofs, 
    read_device_proofs_of_register, 
    write_device_channel, 
    lookup_device_channel
}