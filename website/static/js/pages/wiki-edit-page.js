'use strict';

var $ = require('jquery');
var Raven = require('raven-js');
require('bootstrap-editable');
require('osf-panel');
var WikiPage = require('wikiPage');

require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');

var $osf = require('js/osfHelpers');


var ctx = window.contextVars.wiki;  // mako context variables

var editable = (ctx.panelsUsed.indexOf('edit') !== -1);
var viewable = (ctx.panelsUsed.indexOf('view') !== -1);
var comparable = (ctx.panelsUsed.indexOf('compare') !== -1);
var menuVisible = (ctx.panelsUsed.indexOf('menu') !== -1);

var viewVersion = ctx.versionSettings.view || (editable ? 'preview' : 'current');
var compareVersion = ctx.versionSettings.compare || 'previous';

var wikiPageOptions = {
    editVisible: editable,
    viewVisible: viewable,
    compareVisible: comparable,
    menuVisible: menuVisible,
    canEdit: ctx.canEdit,
    viewVersion: viewVersion,
    compareVersion: compareVersion,
    urls: ctx.urls,
    metadata: ctx.metadata
};

var wikiPage = new WikiPage('#wikiPageContext', wikiPageOptions);
//Probably not where I want to put this or how I want to do this. Reload goes somewhere else.
function ViewModelEditable(){
    var self = this;

    self.makePubliclyEditable = function() {
        $.post('permissions/public/');
        location.reload();
    };

    self.makePrivatelyEditable = function() {
        $.post('permissions/private/');
        location.reload();
    };

}

$osf.applyBindings(new ViewModelEditable(),'#makeEditable');

// Edit wiki page name
if (ctx.canEditPageName) {
    // Initialize editable wiki page name
    var $pageName = $('#pageName');
    $.fn.editable.defaults.mode = 'inline';
    $pageName.editable({
        type: 'text',
        send: 'always',
        url: ctx.urls.rename,
        ajaxOptions: {
            type: 'put',
            contentType: 'application/json',
            dataType: 'json'
        },
        validate: function(value) {
            if($.trim(value) === ''){
                return 'The wiki page name cannot be empty.';
            } else if(value.length > 100){
                return 'The wiki page name cannot be more than 100 characters.';
            }
        },
        params: function(params) {
            return JSON.stringify(params);
        },
        success: function(response, value) {
            window.location.href = ctx.urls.base + encodeURIComponent(value) + '/';
        },
        error: function(response) {
            var msg = response.responseJSON.message_long;
            if (msg) {
                return msg;
            } else {
                // Log unexpected error with Raven
                Raven.captureMessage('Error in renaming wiki', {
                    url: ctx.urls.rename,
                    responseText: response.responseText,
                    statusText: response.statusText
                });
                return 'An unexpected error occurred. Please try again.';
            }
        }
    });
}

// Apply panels
$(document).ready(function () {
    var bodyElement = $('body');

    $('*[data-osf-panel]').osfPanel({
        buttonElement : '.switch',
        onSize : 'xs',
        'onclick' : function (event, title, buttonState, thisbtn, col) {
            // this = all the column elements; an array
            // title = Text of the button
            // buttonState = the visibility of column after click, taen from data-osf-toggle attribute,
            // thisbtn = $(this);
            // col = the $() for the column this button links to

            // Determine if any columns are visible
            var visibleColumns = this.filter(function (i, element) {
                return $(element).is(':visible');
            });

            if (visibleColumns.length === 0) {
                thisbtn.click();
                return;
            }

            bodyElement.trigger('togglePanel', [
                title.toLowerCase(),
                buttonState
            ]);
            if (typeof editor !== 'undefined') { ace.edit(editor).resize(); } // jshint ignore: line
        }
    });

    var panelToggle = $('.panel-toggle');
    var panelExpand = $('.panel-expand');
    $('.panel-collapse').on('click', function () {
        var el = $(this).closest('.panel-toggle');
        el.children('.osf-panel.hidden-xs').addClass('hidden');
        panelToggle.removeClass('col-sm-3').addClass('col-sm-1');
        panelExpand.removeClass('col-sm-9').addClass('col-sm-11');
        el.children('.panel-collapsed').removeClass('hidden');
        $('.wiki-nav').removeClass('hidden');

        bodyElement.trigger('toggleMenu', [false]);
    });
    $('.panel-collapsed .osf-panel-header').on('click', function () {
        var el = $(this).parent();
        var toggle = el.closest('.panel-toggle');
        toggle.children('.osf-panel').removeClass('hidden');
        el.addClass('hidden');
        panelToggle.removeClass('col-sm-1').addClass('col-sm-3');
        panelExpand.removeClass('col-sm-11').addClass('col-sm-9');
        $('.wiki-nav').addClass('hidden');
        bodyElement.trigger('toggleMenu', [true]);
    });

    // Tooltip
    $('[data-toggle="tooltip"]').tooltip();
});
