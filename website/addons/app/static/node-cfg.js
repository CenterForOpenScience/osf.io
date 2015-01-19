var AppNodeConfig = require('./appNodeConfig.js');

var url = window.contextVars.node.urls.api.replace('project', 'app') + 'routes/';
new AppNodeConfig('#appScope', url);
