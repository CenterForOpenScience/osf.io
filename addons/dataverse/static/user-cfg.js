var $osf = require('js/osfHelpers');
var DataverseViewModel = require('./dataverseUserConfig.js').DataverseViewModel;

// Endpoint for Dataverse user settings
var url = '/api/v1/settings/dataverse/';

var dataverseViewModel = new DataverseViewModel(url);
$osf.applyBindings(dataverseViewModel, '#dataverseAddonScope');

// Load initial Dataverse data
dataverseViewModel.fetch();
