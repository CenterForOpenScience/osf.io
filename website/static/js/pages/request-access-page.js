'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var RequestAccessViewModel = require('js/requestAccess');

var ctx = window.contextVars;


$(document).ready(function() {
    var viewModel = new RequestAccessViewModel(ctx.currentUserRequestState, ctx.nodeId);
    $osf.applyBindings(viewModel, '#requestAccessPrivateScope');
});
