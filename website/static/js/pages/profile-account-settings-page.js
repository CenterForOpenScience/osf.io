'use strict';
require('js/affix-menu');

var $ = require('jquery');
var $osf = require('js/osfHelpers.js');
var accountSettings = require('js/accountSettings.js');

$(function() {
    var viewModel = new accountSettings.UserProfileViewModel();
    $osf.applyBindings(viewModel, '#connectedEmails');
    viewModel.init();

    $osf.applyBindings(
        new accountSettings.DeactivateAccountViewModel(),
        '#deactivateAccount'
    );

    $osf.applyBindings(
        new accountSettings.ExportAccountViewModel(),
        '#exportAccount'
    );
});