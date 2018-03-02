'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
var RequestAccessViewModel = require('js/requestAccess');

var ctx = window.contextVars;


$(window).on('load', function() {
    var viewModel = new RequestAccessViewModel(ctx.currentUserRequestState, ctx.nodeId);
    $osf.applyBindings(viewModel, '#requestAccessPrivateScope');
    $('#supportMessage').html('If this should not have occured, please contact ' + $osf.osfSupportLink() + '.');
});
