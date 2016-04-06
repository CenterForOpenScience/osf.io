/**
 * registration retraction ES
**/

var RegistrationRetraction = require('js/registrationRetraction');

var submitUrl = window.contextVars.node.urls.api + 'withdraw/';

var registrationTitle = window.contextVars.node.title;

new RegistrationRetraction.RegistrationRetraction('#registrationRetraction', submitUrl, registrationTitle);
