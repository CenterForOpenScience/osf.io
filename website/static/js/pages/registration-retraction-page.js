/**
 * On page load, focuses on justification input and
 * maintains knockout ViewModel
**/

var $ = require('jquery');

var RegistrationRetraction = require('../registrationRetraction.js');

var submitUrl = contextVars.node.urls.api + 'retract_registration/';

new RegistrationRetraction('#registrationRetraction', submitUrl);

$( document ).ready(function() {
    $('#justificationInput').focus()
});