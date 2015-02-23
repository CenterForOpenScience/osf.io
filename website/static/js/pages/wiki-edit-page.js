var $ = require('jquery');
var Raven = require('raven-js');
var $osf = require('osfHelpers');
require('bootstrap-editable');
require('osf-panel');
var WikiPage = require('wikiPage');

require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');


var ctx = window.contextVars.wiki;  // mako context variables

var selectViewVersion = $('#viewVersionSelect');
var selectCompareVersion = $('#compareVersionSelect');
var previewElement = $('#viewPreview');
var versionElement = $('#viewVersion');
var markdownElement = $('#markdownItRender');
var compareElement = $('#viewCompare');

var editable = (ctx.panelsUsed.indexOf('edit') !== -1);
var viewable = (ctx.panelsUsed.indexOf('view') !== -1);
var comparable = (ctx.panelsUsed.indexOf('compare') !== -1);

var wikiPageOptions = {
    editVisible: editable,
    viewVisible: viewable,
    compareVisible: comparable,
    canEdit: ctx.canEdit,
    viewVersion: 'current',
    compareVersion: 'current',
    urls: ctx.urls,
    metadata: ctx.metadata
};

var wikiPage = new WikiPage('#wikiPageContext', wikiPageOptions);


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
    $('*[data-osf-panel]').osfPanel({
        buttonElement : '.switch',
        onSize : 'md',
        'onclick' : function (title, thisbtn, event ) {
            // this = all the column elements; an array
            // title = Text of the button
            // thisbtn = $(this);
            // thisbtn.hasClass('btn-primary')

            $('body').trigger('togglePanel', [
                title.toLowerCase(),
                thisbtn.hasClass('btn-primary')
            ]);

            if (typeof editor !== 'undefined') { ace.edit(editor).resize(); }

        }
    });

    var panelToggle = $('.panel-toggle'),
        panelExpand = $('.panel-expand');
    $('.panel-collapse').on('click', function () {
        var el = $(this).closest('.panel-toggle');
        el.children('.wiki-panel.hidden-xs').hide();
        panelToggle.removeClass('col-sm-3').addClass('col-sm-1');
        panelExpand.removeClass('col-sm-9').addClass('col-sm-11');
        el.children('.panel-collapsed').show();
        $('.wiki-nav').show();
    });
    $('.panel-collapsed .wiki-panel-header').on('click', function () {
        var el = $(this).parent(),
            toggle = el.closest('.panel-toggle');
        toggle.children('.wiki-panel').show();
        el.hide();
        panelToggle.removeClass('col-sm-1').addClass('col-sm-3');
        panelExpand.removeClass('col-sm-11').addClass('col-sm-9');
        $('.wiki-nav').hide();
    });

    var options = ctx.viewSettings;
    var menu = 'menu' in options;
    var edit = 'edit' in options;
    var compare = 'compare' in options;
    var view = 'view' in options;
    // TODO: toggle menu based on url
    // TODO: Change version select on toggle

    if (edit) {
        selectViewVersion.val('preview');
        selectViewVersion.change();
    }

    if (compare && parseInt(options.compare) === options.compare) {
        selectCompareVersion.val(options.compare);
        selectCompareVersion.change();
    }

    if (view) {
        selectViewVersion.val(options.view);
        selectViewVersion.change();
    }
});
