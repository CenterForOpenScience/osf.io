'use strict';

require('./dropbox.css');
var AddonNodeConfig = require('../../../static/js/addonNodeConfig');

var url = window.contextVars.node.urls.api + 'dropbox/config/';
new AddonNodeConfig('Dropbox', '#dropboxScope', url, '#myDropboxGrid');
