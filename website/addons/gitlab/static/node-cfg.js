'use strict';

var $ = require('jquery');
require('./gitlab-node-cfg.js');
var AddonHelper = require('js/addonHelper');

$(window.contextVars.gitlabSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
