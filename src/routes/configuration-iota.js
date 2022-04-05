const { ApiVersion, ClientConfig } =require('@iota/is-client');
// import { ManagerConfig } from './manager/manager-config';
const dotenv = require('dotenv');

dotenv.config();

const defaultConfig = {
    isGatewayUrl: process.env.API_URL,
    apiKey: process.env.API_KEY,
    apiVersion: ApiVersion.v01
};

module.exports = {defaultConfig};
// export const defaultManagerConfig: ManagerConfig = {
//     mongoURL: process.env.MONGO_URL!,
//     databaseName: process.env.DB_NAME!,
//     secretKey: process.env.SECRET_KEY!
// };