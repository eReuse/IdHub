const multiacc = require('./multiacc-helper.js');
const storage = require('node-persist');

async function initial_steps(){
    await storage.init()
    await multiacc.set_admin()
  }

module.exports = {
    initial_steps
}