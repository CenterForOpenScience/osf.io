'use strict';

var $ = require('jquery');
var AddonHelper = require('js/addonHelper');
var S3NodeConfig = require('./s3NodeConfig').S3NodeConfig;

var ctx = window.contextVars;  // mako context variables

var s3Settings = {
    url: ctx.node.urls.api + 's3/settings/',
};

new S3NodeConfig('#s3Scope', s3Settings);
