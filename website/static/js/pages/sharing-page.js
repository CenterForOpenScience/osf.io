'use strict';
var $ = require('jquery');

var ContribManager = require('js/contribManager');
var ContribAdder = require('js/contribAdder');
var ContribRemover = require('js/contribRemover');
var PrivateLinkManager = require('js/privateLinkManager');
var PrivateLinkTable = require('js/privateLinkTable');

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
        new ContribRemover(
            '#batchRemoveContribs',
            data.node.title,
            data.parent_node.id,
            data.parent_node.title
        );
    }
});

new ContribManager('#manageContributors', ctx.contributors, ctx.adminContributors, ctx.user, ctx.isRegistration);

if ($.inArray('admin', ctx.user.permissions) !== -1) {
    // Controls the modal
    var configUrl = ctx.node.urls.api + 'get_editable_children/';
    var privateLinkManager = new PrivateLinkManager('#addPrivateLink', configUrl);
    var tableUrl = nodeApiUrl + 'private_link/';
    var privateLinkTable = new PrivateLinkTable('#linkScope', tableUrl, ctx.node.isPublic);
    $('#privateLinkTable').on('click', '.link-url', function(e) { e.target.select(); });
}

$(function() {
    $('.admin-info').popover({
        trigger: 'hover'
    });
});
