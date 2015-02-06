var $ = require('jquery');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');

//initialize treebeard
var ProjectNotifications = require('./project-settings-treebeard.js');
new ProjectNotifications(window.contextVars.notificationsData);
