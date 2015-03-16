/**
 * registration retraction ES
**/

var RegistrationRetraction = require('js/registrationRetraction.js');

var submitUrl = contextVars.node.urls.api + 'retract_registration/';

new RegistrationRetraction.RegistrationRetraction('#registrationRetraction', submitUrl);
