'use strict';

var azureblobstorageNodeConfig = require('./azureblobstorageNodeConfig.js').azureblobstorageNodeConfig;

var url = window.contextVars.node.urls.api + 'azureblobstorage/settings/';

new azureblobstorageNodeConfig('Azure Blob Storage', '#azureblobstorageScope', url, '#azureblobstorageGrid');
