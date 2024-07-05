var $osf = require('js/osfHelpers');
var BoaUserConfig = require('./boaUserConfig.js').BoaUserConfig;

var url = '/api/v1/settings/boa/accounts/';
var boaUserConfig = new BoaUserConfig('#boaAddonScope',url);
boaUserConfig.viewModel.fetch();
