'use strict';

var viewModels = require('../apiApplication.js');

var ctx = window.contextVars;
var apiApplication = new viewModels.ApplicationDetail('#app-detail', ctx.urls);
ctx.apiApplication = apiApplication;
