/**
 * On page load, focuses on justification input and
 * maintains knockout ViewModel
**/

var $ = require('jquery');

var RegistrationRetraction = require('../registrationRetraction.js');

// TODO(hrybacki): Handle /project/<pid>/node/<nid>/ URL construction
var getSubmitUrl = function() {
    return '/api/v1/project/' + contextVars.node.id + '/retract_registration/'
};

new RegistrationRetraction('#registrationRetraction', getSubmitUrl());

console.log(getSubmitUrl());

$( document ).ready(function() {
    $('#justificationInput').focus()
});