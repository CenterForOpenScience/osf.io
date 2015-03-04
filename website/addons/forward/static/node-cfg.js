var ForwardConfig = require('./forwardConfig.js');

var url = window.contextVars.node.urls.api + 'forward/config/';
new ForwardConfig('#forwardScope', url, window.contextVars.node.id);