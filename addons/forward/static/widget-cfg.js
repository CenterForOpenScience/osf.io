var ForwardWidget = require('./forwardWidget.js');

var url = window.contextVars.node.urls.api + 'forward/config/';
// #forwardScope will only be present if Forward addon is configured
if ($('#forwardScope')[0]) {
    new ForwardWidget('#forwardScope', url);
}
