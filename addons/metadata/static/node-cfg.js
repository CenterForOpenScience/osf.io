const MetadataNodeConfig = require('./metadataNodeConfig.js');
const SHORT_NAME = 'metadata';
const nodeId = window.contextVars.node.id;
const url = window.contextVars.node.urls.api + SHORT_NAME + '/settings/';
new MetadataNodeConfig('#' + SHORT_NAME + 'Scope', nodeId, url);
