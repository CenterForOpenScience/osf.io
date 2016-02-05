'use strict';
var $ = require('jquery');

var ContribManager = require('js/contribManager');
var ContribAdder = require('js/contribAdder');
var PrivateLinkManager = require('js/privateLinkManager');
var PrivateLinkTable = require('js/privateLinkTable');
var ko = require('knockout');
var rt = require('js/responsiveTable');
require('jquery-ui');
require('js/filters');


var ctx = window.contextVars;

var nodeApiUrl = ctx.node.urls.api;

$('body').on('nodeLoad', function(event, data) {
    // If user is a contributor, initialize the contributor modal
    // controller
    if (data.user.can_edit) {
        new ContribAdder(
            '#addContributors',
            data.node.title,
            data.node.id,
            data.parent_node.id,
            data.parent_node.title
        );
    }
});

var cm = new ContribManager('#manageContributors', ctx.contributors, ctx.adminContributors, ctx.user, ctx.isRegistration, '#manageContributorsTable', '#adminContributorsTable');

if ($.inArray('admin', ctx.user.permissions) !== -1) {
    // Controls the modal
    var configUrl = ctx.node.urls.api + 'get_editable_children/';
    var privateLinkManager = new PrivateLinkManager('#addPrivateLink', configUrl);
    var tableUrl = nodeApiUrl + 'private_link/';
    var linkTable = $('#privateLinkTable');
    var privateLinkTable = new PrivateLinkTable('#linkScope', tableUrl, ctx.node.isPublic, linkTable);
}

$(function() {
    $('.admin-info').popover({
        trigger: 'hover'
    });
});

$(window).load(function() {
    cm.viewModel.onWindowResize();
    if (!!privateLinkTable){
        privateLinkTable.viewModel.onWindowResize();
        rt.responsiveTable(linkTable[0]);
    }
    $('table.responsive-table td:first-child a,' +
        'table.responsive-table td:first-child button').on('click', function(e) {
        e.stopImmediatePropagation();
    });
});

$(window).resize(function() {
    if (!!privateLinkTable) {
        privateLinkTable.viewModel.onWindowResize();
    }
    cm.viewModel.onWindowResize();
});
