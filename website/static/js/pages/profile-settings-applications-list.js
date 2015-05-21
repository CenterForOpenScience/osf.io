'use strict';

var viewModels = require('../apiApplication.js');


var ctx = window.contextVars;
// Instantiate all the profile modules
var apiApplication = new viewModels.ApplicationsList('#app-list', ctx.appListUrls);

ctx.apiApplication = apiApplication;
//new apiApplications.Applications('#app-list', ctx.appDetailUrls, ['view']);
