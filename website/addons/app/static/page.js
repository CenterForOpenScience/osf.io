var ApplicationView = require('./appNodeConfig');

var url = contextVars.node.urls.api.replace('project', 'app');
new ApplicationView('#application', url);
