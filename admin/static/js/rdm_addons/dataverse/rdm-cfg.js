var ko = require('knockout');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var DataverseViewModel = require('./dataverseRdmConfig.js').DataverseViewModel;

// Endpoint for Dataverse user settings
var institutionId = $('#dataverseAddonScope').data('institution-id');
var url = '/addons/api/v1/settings/dataverse/' + institutionId + '/';

var dataverseViewModel = new DataverseViewModel(url, institutionId);
ko.applyBindings(dataverseViewModel, document.getElementById('dataverseAddonScope'));

// Load initial Dataverse data
dataverseViewModel.fetch();
