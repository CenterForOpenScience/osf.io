var pointers = require('../pointers.es6.js');
var AccountClaimer = require('../accountClaimer.js');
var $osf = require('osfHelpers');

// NodeActions is needed for rendering recent logs in nodelists (e.g. regsitrations and forks
// pages
require('../project.js');

var node = window.contextVars.node;


new pointers.PointerDisplay('#showLinks');

if (!window.contextVars.currentUser.isContributor) {
    new AccountClaimer('.contributor-unregistered');
}

if (node.isPublic && node.piwikSiteID) {
    $osf.trackPiwik(node.piwikHost, node.piwikSiteID);
}

$.getJSON(node.urls.api, function(data) {
    $('body').trigger('nodeLoad', data);
});
