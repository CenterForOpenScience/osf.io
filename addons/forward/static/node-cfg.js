var ForwardConfig = require('./forwardConfig.js');

var url = window.contextVars.node.urls.api + 'forward/config/';
// #forwardScope will only be in the DOM if the addon is properly configured
if ($('#forwardScope')[0]) {
    new ForwardConfig('#forwardScope', url, window.contextVars.node.id);
}
