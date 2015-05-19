'use strict';

var apiApplications = require('../apiApplications.js');
var profile = require('../profile.js');


var ctx = window.contextVars;
// Instantiate all the profile modules
var Application = new profile.Applications('#app-list', ctx.appListUrls, ['view']);

//new apiApplications.Applications('#app-list', ctx.appDetailUrls, ['view']);
