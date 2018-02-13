'use strict';

var $osf = require('js/osfHelpers');
var requestAccess = require('js/requestAccess');


var viewModel = new requestAccess.RequestAccessViewModel();
$osf.applyBindings(viewModel, '#requestAccessScope');
viewModel.init();
