const iota = require('./iota/iota-helper.js')
const multiacc = require('./multiacc-helper.js');

async function initial_steps(){
    await iota.check_iota_index()
    await multiacc.set_admin()
  }

module.exports = {
    initial_steps
}