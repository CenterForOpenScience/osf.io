var pointers = require('../pointers.js');
var AccountClaimer = require('../accountClaimer.js');
var $osf = require('osfHelpers');
var NodeControl = require('../nodeControl.js');

// NodeActions is needed for rendering recent logs in nodelists (e.g. regsitrations and forks
// pages
require('../project.js');

var node = window.contextVars.node;
// Get project data from the server and initiate KO modules
$.getJSON(node.urls.api, function(data) {
    // Initialize nodeControl 
    new NodeControl('#projectScope', data);
    $('body').trigger('nodeLoad', data);
});

new pointers.PointerDisplay('#showLinks');

if (!window.contextVars.currentUser.isContributor) {
    new AccountClaimer('.contributor-unregistered');
}

if (node.isPublic && node.piwikSiteID) {
    $osf.trackPiwik(node.piwikHost, node.piwikSiteID);
}
