var AddonHelper = require('addon-helpers');
var $osf = require('osf-helpers');
var bootbox = require('bootbox');
require('./github-node-cfg.js');

$(window.contextVars.githubSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
