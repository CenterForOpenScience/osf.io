var $osf = require('js/osfHelpers');
var FedoraUserConfig = require('./FedoraUserConfig.js').FedoraUserConfig;

var url = '/api/v1/settings/fedora/accounts/';
var FedoraUserConfig = new FedoraUserConfig('#fedoraAddonScope',url);
FedoraUserConfig.viewModel.fetch();
