'use strict';

var OneDriveBusinessUserConfig = require('./onedrivebusinessUserConfig.js').OneDriveBusinessUserConfig;
var url = '/api/v1/settings/onedrivebusiness/accounts/';
new OneDriveBusinessUserConfig('#onedrivebusinessAddonScope', url);
