
var pointers = require('../pointers.js');
var AccountClaimer = require('../accountClaimer.js');
var $osf = require('osf-helpers');

var node = window.contextVars.node;

new pointers.PointerDisplay('#showLinks');

if (!window.contextVars.currentUser.isContributor) {
    new AccountClaimer('.contributor-unregistered');
}


if (node.isPublic && node.piwikSiteID) {
    $osf.trackPiwik(node.piwikHost, node.piwikSiteID);
}
