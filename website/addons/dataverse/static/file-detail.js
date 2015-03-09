var DataverseFileTable = require('./dataverseViewFile.js');

var url = window.contextVars.node.urls.info;
new DataverseFileTable('#dataverseScope', url);