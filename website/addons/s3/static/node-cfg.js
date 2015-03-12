var S3Config = require('./s3NodeSettings');

var url = window.contextVars.node.urls.api + 's3/settings/';
new S3Config('#s3Scope', url);
