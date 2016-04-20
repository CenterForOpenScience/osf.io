'use strict';
var $ = require('jquery');

var ContribManager = require('js/contribManager');

var PrivateLinkManager = require('js/privateLinkManager');
var PrivateLinkTable = require('js/privateLinkTable');
var ko = require('knockout');  // TODO: Why is this required? Is it?
var rt = require('js/responsiveTable');
require('jquery-ui');
require('js/filters');


var ctx = window.contextVars;

var nodeApiUrl = ctx.node.urls.api;

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
