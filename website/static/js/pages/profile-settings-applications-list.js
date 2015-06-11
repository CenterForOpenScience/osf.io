'use strict';

var viewModels = require('../apiApplication.js');

var ctx = window.contextVars;
var apiApplication = new viewModels.ApplicationsList('#app-list', ctx.urls);
ctx.apiApplication = apiApplication;
