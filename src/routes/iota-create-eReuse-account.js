const { IdentityClient, CredentialTypes, UserType, IdentityJson } =require('@iota/is-client');
const { defaultConfig } = require('./configuration-iota');
const fs = require('fs');

async function createIdentityAndCheckVCs() {
  const identity = new IdentityClient(defaultConfig);

  // Recover the admin identity
  //const adminIdentity = JSON.parse(readFileSync('./adminIdentity.json').toString());

  // Authenticate as the admin identity
  //await identity.authenticate(adminIdentity.doc.id, adminIdentity.key.secret);
  // await identity.authenticate("did:iota:8fnveihkLGWeM4AhQdbF98kK5oQzmV4Lq3fzAzg5JeSu", "Ejc9f5NvEvTWtCLpCB61cbANV8jkrK4HkYdEogf1cvz");

  // Get admin identity data
  //const adminIdentityPublic = await identity.find(adminIdentity.doc.id);

  // Get admin identy's VC
  //const identityCredential = adminIdentityPublic?.verifiableCredentials?.[0];

  //console.log('Identity Credential of Admin', identityCredential);

  // Create identity for user
  const username = 'eReuse-test-' + Math.ceil(Math.random() * 100000);
  const userIdentity = await identity.create(username);

  console.log('~~~~~~~~~~~~~~~~');
  console.log('Created user identity: ', userIdentity);
  console.log('~~~~~~~~~~~~~~~~');

  var jsonContent = JSON.stringify(userIdentity)
  fs.writeFile(`${username}-identity.json`, jsonContent, 'utf8', function (err) {
    if (err) {
        console.log("An error occured while writing JSON Object to File.");
        return console.log(err);
    }
 
    console.log("JSON file has been saved.");
});

  // Assign a verifiable credential to the user as rootIdentity.
  // With the BasicIdentityCredential the user is not allowed to issue further credentials
  // const userCredential = await identity.createCredential(
  //   identityCredential,
  //   userIdentity?.doc?.id,
  //   CredentialTypes.BasicIdentityCredential,
  //   UserType.Person,
  //   {
  //     profession: 'Professor'
  //   }
  // );

  // console.log('Created credential: ', userCredential);
  // console.log('~~~~~~~~~~~~~~~~');
  // // Verify the credential issued
  // const verified = await identity.checkCredential(userCredential);

  // console.log('Verification result: ', verified);
}

createIdentityAndCheckVCs();