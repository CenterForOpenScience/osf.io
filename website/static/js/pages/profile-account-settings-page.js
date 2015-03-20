'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers.js');
var accountSettings = require('js/accountSettings.js');

$(function() {
    var viewModel = new accountSettings.userProfile();
    $osf.applyBindings(viewModel, '#accountSettings');
    viewModel.init();
});