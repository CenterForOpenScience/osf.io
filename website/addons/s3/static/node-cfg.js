'use strict';

var $ = require('jquery');
var AddonHelper = require('js/addonHelper');
require('./s3-node-settings.js');

var url = window.contextVars.node.urls.api + 's3/settings/';
var filesUrl = window.contextVars.node.urls.web + 'files/';
new S3NodeConfig('#s3Scope', url, filesUrl);
