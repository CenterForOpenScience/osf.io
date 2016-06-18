'use strict';

var viewModels = require('../apiApplication');
require('css/pages/profile-settings-applications-detail.css');

var ctx = window.contextVars;
var apiApplication = new viewModels.ApplicationDetail('#appDetail', ctx.urls);
