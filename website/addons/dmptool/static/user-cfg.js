var $osf = require('js/osfHelpers');
var dmptoolViewModel = require('./dmptoolUserConfig.js').dmptoolViewModel;

// Endpoint for dmptool user settings
var url = '/api/v1/settings/dmptool/';

var dmptoolViewModel = new dmptoolViewModel(url);
$osf.applyBindings(dmptoolViewModel, '#dmptoolAddonScope');

// Load initial dmptool data
dmptoolViewModel.fetch();