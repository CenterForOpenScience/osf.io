/**
 * registration retraction ES
**/
    
var RegistrationRetraction = require('../registrationRetraction.js');

var submitUrl = contextVars.node.urls.api + 'retract_registration/';

new RegistrationRetraction('#registrationRetraction', submitUrl);
