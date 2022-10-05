import axios from 'axios'

export function getResolver(options) {
  return new EReuseResolver(options).build()
}

export class EReuseResolver {

  constructor(apiUrl) {
    this.apiUrl = apiUrl
  }

  async resolve(
    did,
    parsed,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _unused,
    options
  ) {
    try {
      var res = await axios.post(`${this.apiUrl}/getDidData`,
        { DeviceCHID: parsed.id }, {
        headers: {
          dlt: "ethereum"
        }
      }
      )
      var docData = res.data.data
      var ethChainID = docData.chainid
      var didDocument = {}
      didDocument['@context'] = [
        'https://www.w3.org/ns/did/v1',
        'https://w3id.org/security/suites/secp256k1recovery-2020/v2'
      ]
      didDocument.id = did
      var controller = `did:ethr:${ethChainID}:${docData.controller}`
      didDocument.controller = `did:ethr:${ethChainID}:${docData.controller}`
      didDocument.verificationMethod = []
      var verificationMethodFragment = "#ethkey"
      var mainVerificationMethod = {
        id: `${did}${verificationMethodFragment}`,
        type: 'EcdsaSecp256k1RecoveryMethod2020',
        controller: controller,
        blockchainAccountId: `eip155:${ethChainID}:${docData.controller}`
      }
      didDocument.verificationMethod.push(mainVerificationMethod)
      didDocument.authentication = []
      var mainAuthentication =`${did}${verificationMethodFragment}`
      didDocument.authentication.push(mainAuthentication)
      didDocument.service = []
      var mainServiceFragment = "#smartContract" 
      var mainService = {
        id: `${did}${mainServiceFragment}`,
        type: 'smart_contract',
        serviceEndpoint: `did:ethr:${ethChainID}:${docData.contractAddress}`,
        description: `Smart contract that keeps track of the device's history and supporting DID data.`
      }
      didDocument.service.push(mainService)
      docData.services.forEach(elem => {
        let newService = {}
        newService.id = `${did}#${elem.fragment}`,
        newService.type = elem.type,
        newService.serviceEndpoint = elem.endpoint,
        newService.description = elem.description
        didDocument.service.push(newService)
      })

      return {
        didDocumentMetadata: { },
        didResolutionMetadata: { contentType: 'application/did+ld+json' },
        didDocument,
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (e) {
      return {
        didResolutionMetadata: {
          // error: Errors.notFound
          error: "DID not found.",
          message: e.toString(), // This is not in spec, nut may be helpful
        },
        didDocumentMetadata: {},
        didDocument: null,
      }
    }
  }

  build() {
    return { ereuse: this.resolve.bind(this) }
  }
}
