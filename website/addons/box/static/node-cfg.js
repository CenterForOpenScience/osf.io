'use strict';

var AddonNodeConfig = require('../../../static/js/addonNodeConfig');
var url = window.contextVars.node.urls.api + 'box/config/';
new AddonNodeConfig('Box', '#boxScope', url, '#myBoxGrid');

