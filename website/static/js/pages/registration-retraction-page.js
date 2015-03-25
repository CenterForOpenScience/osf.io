/**
 * registration retraction ES
**/

var RegistrationRetraction = require('js/registrationRetraction');

var submitUrl = window.contextVars.node.urls.api + 'retract_registration/';

var registrationTitle = window.contextVars.node.title;

new RegistrationRetraction.RegistrationRetraction('#registrationRetraction', submitUrl, registrationTitle);
