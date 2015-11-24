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
        ko.contextFor($('#contributors').get(0)).$parent.isSortable(!isFiltered);
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
}

$(function() {
    $('.admin-info').popover({
        trigger: 'hover'
    });
});

var checkWindowWidth = function() {
    if ($('table.responsive-table-xxs thead').is(':hidden')) {
        $('table.responsive-table-xxs tbody tr td:first-child.expanded').siblings().children().css('display', 'block');
        $('table.responsive-table-xxs tbody tr td:first-child').attr('role','button').off().on('click', function() {
            toggleExpand(this.parentElement);
        });
    }
    else {
        $('table.responsive-table-xxs tbody tr:not(:hidden) td>div').css('display', '');
        $('table.responsive-table-xxs tbody tr td:first-child').removeAttr('role');
    }
    if ($('table.responsive-table-xs thead').is(':hidden')) {
        $('table.responsive-table-xs tbody tr td:first-child').attr('role','button').off().on('click', function() {
            toggleExpand(this.parentElement);
        });
    }
    else {
        $('table.responsive-table-xs tbody td>div.header').css('display', '');
        $('table.responsive-table-xs tbody tr td:first-child').removeAttr('role');
    }
};

$(window).load(function() {
    checkWindowWidth();
    var linkTable = $('#privateLinkTable')[0];
    if (linkTable !== undefined) {
        rt.responsiveTable(linkTable);
    }
    $('table.responsive-table td:first-child a,button').on('click', function(e) {
        e.stopImmediatePropagation();
    });
});

$(window).resize(checkWindowWidth);

var toggleExpand = function(el) {
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
    toggleIcon(el);
};

var toggleIcon = function(el) {
    $(el.querySelector('.toggle-icon')).toggleClass('fa-angle-down fa-angle-up');
};
