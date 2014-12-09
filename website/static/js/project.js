/////////////////////
// Project JS      //
/////////////////////
var $ = require('jquery');
var bootbox = require('bootbox');

var LogFeed = require('./logFeed.js');
var osfHelpers = require('./osf-helpers.js');

var NodeActions = {}; // Namespace for NodeActions

// TODO: move me to the NodeControl or separate module
NodeActions.beforeForkNode = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).done(function(response) {
        bootbox.confirm(
            osfHelpers.joinPrompts(response.prompts, 'Are you sure you want to fork this project?'),
            function(result) {
                if (result) {
                    done && done();
                }
            }
        );
    }).fail(
        osfHelpers.handleJSONError
    );
};

NodeActions.forkNode = function() {
    NodeActions.beforeForkNode(nodeApiUrl + 'fork/before/', function() {
        // Block page
        osfHelpers.block();
        // Fork node
        osfHelpers.postJSON(
            nodeApiUrl + 'fork/',
            {}
        ).done(function(response) {
            window.location = response;
        }).fail(function(response) {
            osfHelpers.unblock();
            if (response.status === 403) {
                osfHelpers.growl('Sorry:', 'you do not have permission to fork this project');
            } else {
                osfHelpers.growl('Error:', 'Forking failed');
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
                osfHelpers.block();

                // Fork pointer
                osfHelpers.postJSON(
                    nodeApiUrl + 'pointer/fork/',
                    {pointerId: pointerId}
                ).done(function() {
                    window.location.reload();
                }).fail(function() {
                    osfHelpers.unblock();
                    osfHelpers.growl('Error','Could not fork link.');
                });
            }
        }
    });
};

NodeActions.beforeTemplate = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).success(function(response) {
        bootbox.confirm(
            osfHelpers.joinPrompts(response.prompts,
                ('Are you sure you want to create a new project using this project as a template? ' +
                  'Any add-ons configured for this project will not be authenticated in the new project.')),
            function (result) {
                if (result) {
                    done && done();
                }
            }
        );
    });
};

NodeActions.addonFileRedirect = function(item) {
    window.location.href = item.params.urls.view;
    return false;
};

NodeActions.useAsTemplate = function() {
    NodeActions.beforeTemplate('/project/new/' + nodeId + '/beforeTemplate/', function () {
        osfHelpers.block();

        osfHelpers.postJSON(
            '/api/v1/project/new/' + nodeId + '/',
            {}
        ).done(function(response) {
            window.location = response.url;
        }).fail(function(response) {
            osfHelpers.unblock();
            osfHelpers.handleJSONError(response);
        });
    });
};

$(function() {

    $('#newComponent form').on('submit', function(e) {

        $('#add-component-submit')
            .attr('disabled', 'disabled')
            .text('Adding');

        if ($.trim($('#title').val()) === '') {

            $('#alert').text('The new component title cannot be empty');

            $('#add-component-submit')
                .removeAttr('disabled', 'disabled')
                .text('OK');

            e.preventDefault();
        } else if ($(e.target).find('#title').val().length > 200) {
            $('#alert').text('The new component title cannot be more than 200 characters.');

            $('#add-component-submit')
                .removeAttr('disabled', 'disabled')
                .text('OK');

            e.preventDefault();

        }
    });
});

NodeActions._openCloseNode = function(nodeId) {

    var icon = $('#icon-' + nodeId);
    var body = $('#body-' + nodeId);

    body.toggleClass('hide');

    if (body.hasClass('hide')) {
        icon.removeClass('icon-minus');
        icon.addClass('icon-plus');
        icon.attr('title', 'More');
    } else {
        icon.removeClass('icon-plus');
        icon.addClass('icon-minus');
        icon.attr('title', 'Less');
    }

    // Refresh tooltip text
    icon.tooltip('destroy');
    icon.tooltip();

};


NodeActions.reorderChildren = function(idList, elm) {
    osfHelpers.postJSON(
        nodeApiUrl + 'reorder_components/',
        {new_list: idList}
    ).fail(function(response) {
        $(elm).sortable('cancel');
        osfHelpers.handleJSONError(response);
    });
};

NodeActions.removePointer = function(pointerId, pointerElm) {
    $.ajax({
        type: 'DELETE',
        url: nodeApiUrl + 'pointer/',
        data: JSON.stringify({
            pointerId: pointerId
        }),
        contentType: 'application/json',
        dataType: 'json'
    }).done(function() {
        pointerElm.remove();
    }).fail(
        osfHelpers.handleJSONError
    );
};


/*
Display recent logs for for a node on the project view page.
*/
NodeActions.openCloseNode = function(nodeId) {
    var $logs = $('#logs-' + nodeId);
    if (!$logs.hasClass('active')) {
        if (!$logs.hasClass('served')) {
            $.getJSON(
                $logs.attr('data-uri'),
                {count: 3}
            ).done(function(response) {
                new LogFeed($logs, response.logs);
                $logs.addClass('served');
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
        '<dt>Read</dt><dd>View project content and comment</dd>' +
        '<dt>Read + Write</dt><dd>Read privileges plus add and configure components; add and edit content</dd>' +
        '<dt>Administrator</dt><dd>Read and write privileges; manage contributors; delete and register project; public-private settings</dd>' +
        '</dl>';

    $('.permission-info').attr(
        'data-content', permissionInfoHtml
    ).popover({
        trigger: 'hover'
    });

    var visibilityInfoHtml = 'Only visible contributors will be displayed ' +
        'in the Contributors list and in project citations. Non-visible ' +
        'contributors can read and modify the project as normal.';

    $('.visibility-info').attr(
        'data-content', visibilityInfoHtml
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
            }
        });
    });

    $('body').on('click', '.tagsinput .tag > span', function(e) {
        window.location = '/search/?q=(tags:' + $(e.target).text().toString().trim()+ ')';
    });

    $('.citation-toggle').on('click', function() {
        $(this).closest('.citations').find('.citation-list').slideToggle();
        return false;
    });

});

window.NodeActions = NodeActions;
module.exports = NodeActions;
