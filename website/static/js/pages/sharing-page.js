'use strict';
var $ = require('jquery');

var ContribManager = require('js/contribManager');
var ContribAdder = require('js/contribAdder');
var PrivateLinkManager = require('js/privateLinkManager');
var PrivateLinkTable = require('js/privateLinkTable');
var ko = require('knockout');
var rt = require('js/responsiveTable');
require('jquery-ui');
require('js/cards');
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

$('.filters').filters({
    items: ['.contrib', '.admin'],
    callback: function (filtered, empty) {
        if ($.inArray('.contrib', empty) > -1) {
            $('#noContributors').show();
        }
        else {
            $('#noContributors').hide();
        }
        if ($.inArray('.admin', empty) > -1) {
            $('#noAdminContribs').show();
        }
        else {
            $('#noAdminContribs').hide();
        }
        var isFiltered = $.inArray('.contrib', filtered) > -1;
        ko.contextFor($('#contributors').get(0)).$parent.sortable(isFiltered);
    },
    groups: {
        permissionFilter: {
            filter: '.permission-filter',
            type: 'text',
            buttons: {
                admins: 'Administrator',
                write: 'Read + Write',
                read: 'Read'
                }
        },
        visibleFilter: {
            filter: '.visible-filter',
            type: 'checkbox',
            buttons: {
                visible: true,
                notVisible: false
            }
        }
    },
    inputs: {
        nameSearch: '.name-search'
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

var checkWindowWidth = function() {
    if ($(window).width() <= 600) {
        $('table.responsive-table-xxs tbody tr td:first-child').attr('role','button').attr('onclick', 'toggleExpand(this.parentElement)');
    }
    else {
        $('table.responsive-table-xxs tbody tr:not(:hidden) td>div.header').css('display', '');
        $('table.responsive-table-xxs tbody tr td:first-child').removeAttr('role').removeAttr('onclick');
    }
    if ($(window).width() <= 768) {
        $('table.responsive-table-xs tbody tr td:first-child').attr('role','button').attr('onclick', 'toggleExpand(this.parentElement)');
    }
    else {
        $('table.responsive-table-xs tbody td>div.header').css('display', '');
        $('table.responsive-table-xs tbody tr td:first-child').removeAttr('role').removeAttr('onclick');
    }
};

$(window).load(function() {
    checkWindowWidth();
    var linkTable = $('#privateLinkTable')[0];
    if (linkTable !== undefined) {
        rt.responsiveTable(linkTable);
    }
});

$(window).resize(function() {
    checkWindowWidth();
});

window.toggleExpand = function(el) {
    var $self = $(el.querySelectorAll('td:not(:first-child):not(.table-only)>div'));
    if ($self.is(':hidden')) {
        $(el.firstElementChild).toggleClass('expanded');
        $self.slideToggle();
    }
    else {
        $self.slideToggle(function() {
            if ($(el.firstElementChild).is('.expanded')){
                $(el.firstElementChild).toggleClass('expanded');
            }
        });
    }
    window.toggleIcon(el);
};
