var AddonHelper = require('addonHelper');
var $ = require('jquery');
require('./github-node-cfg.js');

$(window.contextVars.githubSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
