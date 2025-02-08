/////////////////////
// Project JS      //
/////////////////////
'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var ko = require('knockout');

var _ = require('js/rdmGettext')._;

var $osf = require('js/osfHelpers');

var ctx = window.contextVars;
var NodeActions = {}; // Namespace for NodeActions
require('loaders.css/loaders.min.css');
require('css/add-project-plugin.css');
const LIMITED_ERROR = 'The new project cannot be created due to the created project number is greater than or equal the project number can create.';


// TODO: move me to the NodeControl or separate module
NodeActions.beforeForkNode = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).done(function(response) {
        bootbox.confirm({
            message: $osf.joinPrompts(response.prompts, (_('<h4>Are you sure you want to fork this project?</h4>'))),
            callback: function (result) {
                if (result) {
                    done && done();
                }
            },
            buttons:{
                confirm:{
                    label:_('Fork')
                },
                cancel:{
                    label:_('Cancel')
                }
            }
        });
    }).fail(
        $osf.handleJSONError
    );
};

function afterForkGoto(url) {
  bootbox.confirm({
      message: '<h4 class="add-project-success text-success">' + _('Fork created successfully!') + '</h4>',
      callback: function(result) {
          if(result) {
              window.location = url;
          }
      },
      buttons: {
          confirm: {
              label: _('Go to new fork'),
              className: 'btn-success'
          },
          cancel: {
              label: _('Keep working here')
          }
      },
      closeButton: false
  });
}

NodeActions.forkNode = function() {
    NodeActions.beforeForkNode(ctx.node.urls.api + 'fork/before/', function() {
        // Block page
        var payload = {
            data: {
                type: 'nodes'
            }
        };
        // Fork node
        var nodeType = ctx.node.isRegistration ? 'registrations' : 'nodes';
        $osf.ajaxJSON(
            'POST',
            $osf.apiV2Url(nodeType + '/' + ctx.node.id + '/forks/'),
            {
                isCors: true,
                data: payload
            }
        ).done(function(){
            $osf.growl('Fork status', _('Your fork is being created. You\'ll receive an email when it is complete.'), 'info');
        }).fail(function(response){
            // Check response has project limit number error
            var error_detail = '';
            if (response.responseJSON && response.responseJSON.errors && response.responseJSON.errors.length > 0){
                error_detail = response.responseJSON.errors[0].detail;
            }
            if (error_detail === LIMITED_ERROR){
                $osf.growl('Error', _(error_detail), 'danger');
            } else {
                $osf.growl('Fork status', _('Your fork is being created. You\'ll receive an email when it is complete.'), 'info');
            }
        });
    });
};

NodeActions.forkPointer = function(nodeId) {
    bootbox.confirm({
        title: _('Fork this project?'),
        message: _('Are you sure you want to fork this project?'),
        callback: function(result) {
            if(result) {
                // Block page
                $osf.block();

                // Fork pointer
                $osf.postJSON(
                    ctx.node.urls.api + 'pointer/fork/',
                    {nodeId: nodeId}
                ).done(function(response) {
                    $osf.unblock();
                    afterForkGoto(response.data.node.url);
                }).fail(function(response) {
                    $osf.unblock();
                    // Check response has project limit number error
                    var error_detail = response.responseJSON.message_long ? (response.responseJSON && response.responseJSON.message_long) : '';
                    if (error_detail === LIMITED_ERROR){
                        $osf.growl('Error', _(error_detail));
                    } else {
                        $osf.growl('Error', _('Could not fork link.'));
                    }
                });
            }
        },
        buttons:{
            confirm:{
                label:_('Fork')
            }
        }
    });
};

NodeActions.beforeTemplate = function(url, done) {
    $.ajax({
        url: url,
        contentType: 'application/json'
    }).done(function(response) {
        var language = _('<h4>Are you sure you want to create a new project using this project as a template?</h4>') +
                _('<p>Any add-ons configured for this project will not be authenticated in the new project.</p>');
        if(response.isRegistration){
            language = _('<h4>Are you sure you want to create a new project using this registration as a template?</h4>');
        }
        bootbox.confirm({
            message: $osf.joinPrompts(response.prompts, (language)),
            callback: function (result) {
                if (result) {
                    done && done();
                }
            },
            buttons:{
                confirm:{
                    label:_('Create')
                },
                cancel:{
                    label:_('Cancel')
                }
            }
        });
    });
};

NodeActions.redirectForkPage = function(){
    window.location.href = '/' + ctx.node.id + '/forks/';
    return true;
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

            // Check response has project limit number error
            var error_detail = response.responseJSON.message_long ? (response.responseJSON && response.responseJSON.message_long) : '';
            if (error_detail === LIMITED_ERROR){
                $osf.growl('Error',_(error_detail), 'danger');
            } else {
                $osf.handleJSONError(response);
            }
        });
    });
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

// TODO: remove this
$(document).ready(function() {
    var permissionInfoHtml = '<dl>' +
        _('<dt>Read</dt>') +
            _('<dd><ul><li>View project content and comment</li></ul></dd>') +
        _('<dt>Read + Write</dt>') +
            _('<dd><ul><li>Read privileges</li> ') +
                _('<li>Add and configure components</li> ') +
                _('<li>Add and edit content</li></ul></dd>') +
        _('<dt>Administrator</dt><dd><ul>') +
            _('<li>Read and write privileges</li>') +
            _('<li>Manage contributor</li>') +
            _('<li>Delete and register project</li><li>Public-private settings</li></ul></dd>') +
        '</dl>';

    $('.permission-info').attr(
        'data-content', permissionInfoHtml
    ).popover({
        trigger: 'hover'
    });

    var bibliographicContribInfoHtml = _('Only bibliographic contributors will be displayed in the Contributors list and in project citations. Non-bibliographic contributors can read and modify the project as normal.');

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
            title: _('Remove this link?'),
            message: _('Are you sure you want to remove this link? This will not remove the project this link refers to.'),
            callback: function(result) {
                if(result) {
                    var pointerId = $this.attr('data-id');
                    var pointerElm = $this.closest('.list-group-item');
                    NodeActions.removePointer(pointerId, pointerElm);
                }
            },
            buttons:{
                    confirm:{
                        label:_('Remove'),
                        className:'btn-danger'
                    },
                    cancel:{
                        label:_('Cancel')
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
      if(e){
        window.location = '/search/?q=(tags:"' + $(e.target).text().toString().trim()+ '")';
      }
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
        if (commentsLinkElm) {
            if(!ko.dataFor(commentsLinkElm)) {
                commentsLinkElm.parentNode.removeChild(commentsLinkElm);
            }
        }
    });
});

window.NodeActions = NodeActions;
module.exports = NodeActions;
