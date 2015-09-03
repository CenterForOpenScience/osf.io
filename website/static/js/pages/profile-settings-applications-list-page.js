'use strict';

var viewModels = require('../apiApplication');

var ctx = window.contextVars;
var apiApplication = new viewModels.ApplicationsList('#appList', ctx.urls);
