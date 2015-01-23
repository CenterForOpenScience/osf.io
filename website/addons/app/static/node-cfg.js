var AppNodeConfig = require('./appNodeConfig.js');
var appUrl = window.contextVars.node.urls.api.replace('project', 'app');

var routingUrl = appUrl + 'routes/';
var mappingUrl = appUrl + 'sorting/';

new AppNodeConfig('#appScope', routingUrl, mappingUrl);
