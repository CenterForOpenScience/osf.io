'use strict';

var viewModels = require('../apiApplication.js');


var ctx = window.contextVars;
// Instantiate all the profile modules
var apiApplication = new viewModels.ApplicationDetail('#app-detail', ctx.urls);

ctx.apiApplication = apiApplication;
//new apiApplications.Applications('#app-list', ctx.appDetailUrls, ['view']);
