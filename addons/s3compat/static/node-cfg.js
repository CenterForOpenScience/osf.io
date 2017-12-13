'use strict';

var s3compatNodeConfig = require('./s3compatNodeConfig.js').s3compatNodeConfig;

var url = window.contextVars.node.urls.api + 's3compat/settings/';

new s3compatNodeConfig('S3 Compatible Storage', '#s3compatScope', url, '#s3compatGrid');
