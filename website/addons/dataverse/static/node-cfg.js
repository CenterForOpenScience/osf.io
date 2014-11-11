var DataverseNodeConfig = require('./dataverseNodeConfig.js');

var url = window.contextVars.node.urls.api + 'dataverse/config/';
new DataverseNodeConfig('#dataverseScope', url);
