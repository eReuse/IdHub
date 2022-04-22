const { ApiVersion, ClientConfig } =require('@iota/is-client');
// import { ManagerConfig } from './manager/manager-config';
const dotenv = require('dotenv');

dotenv.config();
// TODO: This dotenv config should be updated. It picks up the .env file from the directory where the node command is called.
// Thus, it will only get the correct data if the API is started from the src/routes directory. 👨‍🦲

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