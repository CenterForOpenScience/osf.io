var ApplicationView = require('./appPage.js');

var url = contextVars.node.urls.api.replace('project', 'app');
new ApplicationView('#application', url);
