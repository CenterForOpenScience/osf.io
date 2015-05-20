var ForwardConfig = require('./forwardConfig.js');

var url = window.contextVars.node.urls.api + 'forward/config/';
if ($('#forwardScope')[0]) {
    new ForwardConfig('#forwardScope', url, window.contextVars.node.id);
}
