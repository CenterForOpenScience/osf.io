'use strict';

var $ = require('jquery');
require('./bitbucket-node-cfg.js');
var AddonHelper = require('js/addonHelper');

$(window.contextVars.bitbucketSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
