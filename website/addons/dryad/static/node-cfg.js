'use strict';

var $ = require('jquery');
require('./dryad-node-config.js');
var AddonHelper = require('js/addonHelper');

$(window.contextVars.dryadSettingsSelector).on('submit', AddonHelper.onSubmitSettings);