var S3NodeConfig = require('./s3NodeConfig').S3NodeConfig;

var url = window.contextVars.node.urls.api + 's3/settings/';
new S3NodeConfig('#s3Scope', url);
