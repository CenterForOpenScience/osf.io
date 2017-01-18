var DataverseNodeConfig = require('./dataverseNodeConfig.js');

var url = window.contextVars.node.urls.api + 'dataverse/settings/';
new DataverseNodeConfig('#dataverseScope', url);
