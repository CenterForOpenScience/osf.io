'use strict';

var $ = require('jquery');
require('./github-node-cfg.js');
var AddonHelper = require('js/addonHelper');

$(window.contextVars.githubSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
