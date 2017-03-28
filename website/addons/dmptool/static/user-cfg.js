var $osf = require('js/osfHelpers');
var DmptoolViewModel = require('./dmptoolUserConfig.js').dmptoolViewModel;

// Endpoint for Dmptool user settings
var url = '/api/v1/settings/dmptool/';

var dmptoolViewModel = new DmptoolViewModel(url);
$osf.applyBindings(dmptoolViewModel, '#dmptoolAddonScope');

// Load initial Dmptool data
dmptoolViewModel.fetch();