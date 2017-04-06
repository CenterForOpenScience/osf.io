'use strict';

var s3NodeConfig = require('./s3NodeConfig.js').s3NodeConfig;

var url = window.contextVars.node.urls.api + 's3/settings/';

new s3NodeConfig('Amazon S3', '#s3Scope', url, '#s3Grid');
