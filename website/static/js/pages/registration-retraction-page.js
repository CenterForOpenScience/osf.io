/**
 * On page load, focuses on justification input and
 * maintains knockout ViewModel
**/

var $ = require('jquery');

var RegistrationRetraction = require('../registrationRetraction.js');

new RegistrationRetraction('#registrationRetraction', '/api/v1/retract_registration/');

$( document ).ready(function() {
    $('#justificationInput').focus()
});