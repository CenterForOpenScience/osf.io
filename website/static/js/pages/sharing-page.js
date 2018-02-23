'use strict';
var $ = require('jquery');

var ContribManager = require('js/contribManager');
var AccessRequestManager = require('js/accessRequestManager');

var PrivateLinkManager = require('js/privateLinkManager');
var PrivateLinkTable = require('js/privateLinkTable');
var rt = require('js/responsiveTable');
require('jquery-ui');
require('js/filters');


var ctx = window.contextVars;

var nodeApiUrl = ctx.node.urls.api;

var isContribPage = $('#manageContributors').length;
var hasAccessRequests = $('#manageAccessRequests').length;
var cm;
var arm;

if (isContribPage) {
    cm = new ContribManager('#manageContributors', ctx.contributors, ctx.adminContributors, ctx.currentUser, ctx.isRegistration, '#manageContributorsTable', '#adminContributorsTable');
}

if (hasAccessRequests) {
    arm = new AccessRequestManager('#manageAccessRequests', ctx.accessRequests, ctx.currentUser, ctx.isRegistration, '#manageAccessRequestsTable');
}

if ($.inArray('admin', ctx.currentUser.permissions) !== -1) {
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

$(window).on('load', function() {
    if (typeof cm !== 'undefined') {
      cm.viewModel.onWindowResize();
    }
    if (typeof arm !== 'undefined') {
      arm.viewModel.onWindowResize();
    }
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
    if (typeof cm !== 'undefined') {
      cm.viewModel.onWindowResize();
    }
    if (typeof arm !== 'undefined') {
      arm.viewModel.onWindowResize();
    }
});
