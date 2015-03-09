var DataverseWidget = require('./dataverseWidget.js');

var url = window.contextVars.node.urls.api + 'dataverse/widget/contents/';
new DataverseWidget('#dataverseScope', url);
