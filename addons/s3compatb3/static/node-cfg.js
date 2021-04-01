'use strict';

var s3compatb3NodeConfig = require('./s3compatb3NodeConfig.js').s3compatb3NodeConfig;

var url = window.contextVars.node.urls.api + 's3compatb3/settings/';

new s3compatb3NodeConfig('Oracle Cloud Infrastructure Object Storage', '#s3compatb3Scope', url, '#s3compatb3Grid');
