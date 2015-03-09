var ForwardWidget = require('./forwardWidget.js');

var url = window.contextVars.node.urls.api + 'forward/config/';
new ForwardWidget('#forwardScope', url);
