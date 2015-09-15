'use strict';

var $ = require('jquery');
var AddonHelper = require('js/addonHelper');

$(window.contextVars.dryadSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
