'use strict';
var $ = require('jquery');
var ContribManager = require('../contribManager.js');
var ContribAdder = require('../contribAdder.js');

var PrivateLinkManager = require('../privateLinkManager.js');
var PrivateLinkTable = require('../privateLinkTable.js');

var ctx = window.contextVars;

var nodeApiUrl = ctx.node.urls.api;

$('body').on('nodeLoad', function(event, data) {
    // If user is a contributor, initialize the contributor modal
    // controller
    if (data.user.can_edit) {
        new ContribAdder(
            '#addContributors',
            data.node.title,
            data.parent_node.id,
            data.parent_node.title
        );
    }
});

new ContribManager('#manageContributors', ctx.contributors, ctx.user, ctx.isRegistration);

if ($.inArray('admin', ctx.user.permissions) !== -1) {
    // Controls the modal
    var configUrl = ctx.node.urls.api + 'get_editable_children/';
    var privateLinkManager = new PrivateLinkManager('#addPrivateLink', configUrl);

    var tableUrl = nodeApiUrl + 'private_link/';
    var privateLinkTable = new PrivateLinkTable('#linkScope', tableUrl);
    $('#privateLinkTable').on('click', '.link-url', function(e) { e.target.select(); });
}
