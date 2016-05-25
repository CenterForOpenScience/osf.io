/////////////////////
// Project JS      //
/////////////////////
'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var ko = require('knockout');

var $osf = require('js/osfHelpers');
var LogFeed = require('js/logFeed.js');

var ctx = window.contextVars;
var NodeActions = {}; // Namespace for NodeActions
require('loaders.css/loaders.min.css');


// TODO: move me to the NodeControl or separate module
NodeActions.beforeForkNode = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).done(function(response) {
        bootbox.confirm({
            message: $osf.joinPrompts(response.prompts, ('<h4>Are you sure you want to fork this project?</h4>')),
            callback: function (result) {
                if (result) {
                    done && done();
                }
            },
            buttons:{
                confirm:{
                    label:'Fork'
                }
            }
        });
    }).fail(
        $osf.handleJSONError
    );
};

NodeActions.forkNode = function() {
    NodeActions.beforeForkNode(ctx.node.urls.api + 'fork/before/', function() {
        // Block page
        $osf.block();
        // Fork node
        $osf.postJSON(
            ctx.node.urls.api + 'fork/',
            {}
        ).done(function(response) {
            window.location = response;
        }).fail(function(response) {
            $osf.unblock();
            if (response.status === 403) {
                $osf.growl('Sorry:', 'you do not have permission to fork this project');
            } else {
                $osf.growl('Error:', 'Forking failed');
                Raven.captureMessage('Error occurred during forking');
            }
        });
    });
};

NodeActions.forkPointer = function(pointerId) {
    bootbox.confirm({
        title: 'Fork this project?',
        message: 'Are you sure you want to fork this project?',
        callback: function(result) {
            if(result) {
                // Block page
                $osf.block();

                // Fork pointer
                $osf.postJSON(
                    ctx.node.urls.api + 'pointer/fork/',
                    {pointerId: pointerId}
                ).done(function() {
                    window.location.reload();
                }).fail(function() {
                    $osf.unblock();
                    $osf.growl('Error','Could not fork link.');
                });
            }
        },
        buttons:{
            confirm:{
                label:'Fork'
            }
        }
    });
};

NodeActions.beforeTemplate = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).success(function(response) {
        bootbox.confirm({
            message: $osf.joinPrompts(response.prompts,
                ('<h4>Are you sure you want to create a new project using this project as a template?</h4>' +
                '<p>Any add-ons configured for this project will not be authenticated in the new project.</p>')),
                //('Are you sure you want to create a new project using this project as a template? ' +
                //  'Any add-ons configured for this project will not be authenticated in the new project.')),
            callback: function (result) {
                if (result) {
                    done && done();
                }
            },
            buttons:{
                confirm:{
                    label:'Create'
                }
            }
        });
    });
};

NodeActions.addonFileRedirect = function(item) {
    window.location.href = item.params.urls.view;
    return false;
};

NodeActions.useAsTemplate = function() {
    NodeActions.beforeTemplate('/project/new/' + ctx.node.id + '/beforeTemplate/', function () {
        $osf.block();

        $osf.postJSON(
            '/api/v1/project/new/' + ctx.node.id + '/',
            {}
        ).done(function(response) {
            window.location = response.url;
        }).fail(function(response) {
            $osf.unblock();
            $osf.handleJSONError(response);
        });
    });
};


$(function() {

    $('#newComponent form').on('submit', function(e) {

        $('#add-component-submit')
            .attr('disabled', 'disabled')
            .text('Adding');

        if ($.trim($('#title').val()) === '') {

            $('#newComponent .modal-alert').text('This field is required.');

            $('#add-component-submit')
                .removeAttr('disabled', 'disabled')
                .text('Add');

            e.preventDefault();
        } else if ($(e.target).find('#title').val().length > 200) {
            $('#newComponent .modal-alert').text('The new component title cannot be more than 200 characters.'); //This alert never appears...

            $('#add-component-submit')
                .removeAttr('disabled', 'disabled')
                .text('Add');

            e.preventDefault();

        }
    });
});

NodeActions._openCloseNode = function(nodeId) {

    var icon = $('#icon-' + nodeId);
    var body = $('#body-' + nodeId);

    body.toggleClass('hide');

    if (body.hasClass('hide')) {
        icon.removeClass('fa fa-angle-up');
        icon.addClass('fa fa-angle-down');
    } else {
        icon.removeClass('fa fa-angle-down');
        icon.addClass('fa fa-angle-up');
    }
};


NodeActions.reorderChildren = function(idList, elm) {
    $osf.postJSON(
        ctx.node.urls.api + 'reorder_components/',
        {new_list: idList}
    ).fail(function(response) {
        $(elm).sortable('cancel');
        $osf.handleJSONError(response);
    });
};

NodeActions.removePointer = function(pointerId, pointerElm) {
    $.ajax({
        type: 'DELETE',
        url: ctx.node.urls.api + 'pointer/',
        data: JSON.stringify({
            pointerId: pointerId
        }),
        contentType: 'application/json',
        dataType: 'json'
    }).done(function() {
        pointerElm.remove();
    }).fail(
        $osf.handleJSONError
    );
};


/*
Display recent logs for for a node on the project view page.
*/
NodeActions.openCloseNode = function(nodeId) {
    var $logs = $('#logs-' + nodeId);
    var $loader = $('#body-' + nodeId + '> .ball-scale');
    if (!$logs.hasClass('active')) {
        if (!$logs.hasClass('served')) {
            $loader.show();
            $.getJSON(
                $logs.attr('data-uri'),
                {count: 3}
            ).done(function(response) {
                $loader.hide();
                new LogFeed('#logs-' + nodeId, response.logs);
                $logs.addClass('served');
            }).fail(function() {
                $loader.hide();
                $osf.growl('Error:', 'Can not show recent activity right now.  Please try again later.');
                Raven.captureMessage('Error occurred retrieving log');
            });
        }
        $logs.addClass('active');
    } else {
        $logs.removeClass('active');
    }
    // Hide/show the html
    NodeActions._openCloseNode(nodeId);
};

// TODO: remove this
$(document).ready(function() {
    var permissionInfoHtml = '<dl>' +
        '<dt>Read</dt>' +
            '<dd><ul><li>View project content and comment</li></ul></dd>' +
        '<dt>Read + Write</dt>' +
            '<dd><ul><li>Read privileges</li> ' +
                '<li>Add and configure components</li> ' +
                '<li>Add and edit content</li></ul></dd>' +
        '<dt>Administrator</dt><dd><ul>' +
            '<li>Read and write privileges</li>' +
            '<li>Manage contributor</li>' +
            '<li>Delete and register project</li><li>Public-private settings</li></ul></dd>' +
        '</dl>';

    $('.permission-info').attr(
        'data-content', permissionInfoHtml
    ).popover({
        trigger: 'hover'
    });

    var bibliographicContribInfoHtml = 'Only bibliographic contributors will be displayed ' +
           'in the Contributors list and in project citations. Non-bibliographic contributors ' +
            'can read and modify the project as normal.';

    $('.visibility-info').attr(
        'data-content', bibliographicContribInfoHtml
    ).popover({
        trigger: 'hover'
    });

    ////////////////////
    // Event Handlers //
    ////////////////////

    $('.remove-pointer').on('click', function() {
        var $this = $(this);
        bootbox.confirm({
            title: 'Remove this link?',
            message: 'Are you sure you want to remove this link? This will not remove the ' +
                'project this link refers to.',
            callback: function(result) {
                if(result) {
                    var pointerId = $this.attr('data-id');
                    var pointerElm = $this.closest('.list-group-item');
                    NodeActions.removePointer(pointerId, pointerElm);
                }
            },
            buttons:{
                    confirm:{
                        label:'Remove',
                        className:'btn-danger'
                    }
            }
        });
    });

    $('#citation-more').on('click', function() {
        var panel = $('#citationStylePanel');
        panel.slideToggle(200, function() {
            if (panel.is(':visible')) {
                $('#citationStyleInput').select2('open');
            }
        });
        return false;
    });

    $('body').on('click', '.tagsinput .tag > span', function(e) {
        window.location = '/search/?q=(tags:"' + $(e.target).text().toString().trim()+ '")';
    });


    // Portlet feature for the dashboard, to be implemented in later versions.
    // $( ".osf-dash-col" ).sortable({
    //   connectWith: ".osf-dash-col",
    //   handle: ".addon-widget-header",
    //   cancel: ".pull-right",
    //   placeholder: "osf-dash-portlet ui-corner-all"
    // });

    // Adds active class to current menu item
    $(function () {
        var path = window.location.pathname;
        $('.project-nav a:not(#commentsLink)').each(function () {
            var href = $(this).attr('href');
            if (path === href ||
               (path.indexOf('files') > -1 && href.indexOf('files') > -1) ||
               (path.indexOf('wiki') > -1 && href.indexOf('wiki') > -1)) {
                $(this).closest('li').addClass('active');
            }
        });

        // Remove Comments link from project nav bar for pages not bound to the comment view model
        var commentsLinkElm = document.getElementById('commentsLink');
        if (!ko.dataFor(commentsLinkElm) && commentsLinkElm != null) {
             commentsLinkElm.remove();
        }
    });
});

window.NodeActions = NodeActions;
module.exports = NodeActions;
