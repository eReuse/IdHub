// Core interfaces
import {
    createAgent,
    IDIDManager,
    IResolver,
    IDataStore,
    IDataStoreORM,
    IKeyManager,
    ICredentialPlugin,
} from '@veramo/core'

// Core identity manager plugin
import { DIDManager } from '@veramo/did-manager'

// Ethr did identity provider
import { EthrDIDProvider } from '@veramo/did-provider-ethr'

// Core key manager plugin
import { KeyManager } from '@veramo/key-manager'

// Custom key management system for RN
import { KeyManagementSystem, SecretBox } from '@veramo/kms-local'

// W3C Verifiable Credential plugin
import { CredentialPlugin } from '@veramo/credential-w3c'

// Custom resolvers
import { DIDResolverPlugin } from '@veramo/did-resolver'
import { Resolver } from 'did-resolver'
import { getResolver as ethrDidResolver } from 'ethr-did-resolver'
import { getResolver as webDidResolver } from 'web-did-resolver'

// Storage plugin using TypeOrm
import { Entities, KeyStore, DIDStore, PrivateKeyStore, migrations } from '@veramo/data-store'

// TypeORM is installed with `@veramo/data-store`
import { DataSource } from 'typeorm'

import {CredentialIssuerEIP712, ICredentialIssuerEIP712} from '@veramo/credential-eip712'



// This will be the name for the local sqlite database for demo purposes
const DATABASE_FILE = 'database.sqlite'

// You will need to get a project ID from infura https://www.infura.io
const INFURA_PROJECT_ID = '<your PROJECT_ID here>'

// This will be the secret key for the KMS
const KMS_SECRET_KEY = "0ddfb86f726a725a9a1d86d041ef9709c7623f2ee00f70a23c72090ef3e28e64"

const dbConnection = new DataSource({
    type: 'sqlite',
    database: DATABASE_FILE,
    synchronize: false,
    migrations,
    migrationsRun: true,
    logging: ['error', 'info', 'warn'],
    entities: Entities,
}).initialize()


export const agent = createAgent<
    IDIDManager & IKeyManager & IDataStore & IDataStoreORM & IResolver & ICredentialPlugin & ICredentialIssuerEIP712
>({
    plugins: [
        new KeyManager({
            store: new KeyStore(dbConnection),
            kms: {
                local: new KeyManagementSystem(new PrivateKeyStore(dbConnection, new SecretBox(KMS_SECRET_KEY))),
            },
        }),
        new DIDManager({
            store: new DIDStore(dbConnection),
            defaultProvider: 'ereuse',
            providers: {
                'ereuse': new EthrDIDProvider({
                    name:"ereuse",
                    defaultKms: 'local',
                    network: 457,
                    rpcUrl: "http://45.150.187.30:8545",
                    registry: "0x65CF661380b57c3a91b6e501D5c4c5a0652b33f0"
                }),
            },
        }),
        new DIDResolverPlugin({
            resolver: new Resolver({
                ...ethrDidResolver({
                    networks: [
                        {
                            name:"mainnet",
                            chainId: 457,
                            rpcUrl: "http://45.150.187.30:8545",
                            registry: "0x65CF661380b57c3a91b6e501D5c4c5a0652b33f0"
                        }
                    ]
                }),
                ...webDidResolver(),
            }),
        }),
        new CredentialPlugin(),
        new CredentialIssuerEIP712(),
    ],
})