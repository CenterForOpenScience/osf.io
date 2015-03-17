/**
 * registration retraction ES
**/

var RegistrationRetraction = require('js/registrationRetraction.js');

var submitUrl = contextVars.node.urls.api + 'retract_registration/';

var registrationTitle = contextVars.node.title;

new RegistrationRetraction.RegistrationRetraction('#registrationRetraction', submitUrl, registrationTitle);
