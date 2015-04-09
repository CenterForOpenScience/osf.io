'use strict';

var $ = require('jquery');
var Raven = require('raven-js');
require('bootstrap-editable');
require('osf-panel');
var FilePage = require('filePage');

require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');

var $osf = require('js/osfHelpers');


var ctx = window.contextVars.files;  // mako context variables

//var editable = (ctx.panelsUsed.indexOf('edit') !== -1);
//var viewable = (ctx.panelsUsed.indexOf('view') !== -1);
//var comparable = (ctx.panelsUsed.indexOf('compare') !== -1);
//var menuVisible = (ctx.panelsUsed.indexOf('menu') !== -1);

//var viewVersion = ctx.versionSettings.view || (editable ? 'preview' : 'current');
//var compareVersion = ctx.versionSettings.compare || 'previous';

var filePageOptions = {
//    editVisible: editable,
//    viewVisible: viewable,
//    compareVisible: comparable,
//    menuVisible: menuVisible,
    canEdit: ctx.canEdit,
//    viewVersion: viewVersion,
//    compareVersion: compareVersion,
    urls: ctx.urls
//    metadata: ctx.metadata
};

var filePage = new FilePage('#filePageContext', filePageOptions);


// Edit wiki page name
//if (ctx.canEditPageName) {
//    // Initialize editable wiki page name
//    var $pageName = $('#pageName');
//    $.fn.editable.defaults.mode = 'inline';
//    $pageName.editable({
//        type: 'text',
//        send: 'always',
//        url: ctx.urls.rename,
//        ajaxOptions: {
//            type: 'put',
//            contentType: 'application/json',
//            dataType: 'json'
//        },
//        validate: function(value) {
//            if($.trim(value) === ''){
//                return 'The wiki page name cannot be empty.';
//            } else if(value.length > 100){
//                return 'The wiki page name cannot be more than 100 characters.';
//            }
//        },
//        params: function(params) {
//            return JSON.stringify(params);
//        },
//        success: function(response, value) {
//            window.location.href = ctx.urls.base + encodeURIComponent(value) + '/';
//        },
//        error: function(response) {
//            var msg = response.responseJSON.message_long;
//            if (msg) {
//                return msg;
//            } else {
//                // Log unexpected error with Raven
//                Raven.captureMessage('Error in renaming wiki', {
//                    url: ctx.urls.rename,
//                    responseText: response.responseText,
//                    statusText: response.statusText
//                });
//                return 'An unexpected error occurred. Please try again.';
//            }
//        }
//    });
//}

// Apply panels
//$(document).ready(function () {
//    var bodyElement = $('body');

//    $('*[data-osf-panel]').osfPanel({

//        'onclick' : function (event, title, buttonState, thisbtn, col) {
            // this = all the column elements; an array
            // title = Text of the button
            // buttonState = the visibility of column after click, taen from data-osf-toggle attribute, 
            // thisbtn = $(this);
            // col = the $() for the column this button links to
            
            // Determine if any columns are visible
//            var visibleColumns = this.filter(function (i, element) {
//                return $(element).is(':visible');
//            });
 
//            if (visibleColumns.length === 0) {
//                thisbtn.click();
//                return;
//            }
            
//            bodyElement.trigger('togglePanel', [
//                title.toLowerCase(),
//                buttonState
//            ]);
//            ace.edit(editor).resize();  // jshint ignore: line
//        }
//    });


    // Tooltip
//    $('[data-toggle="tooltip"]').tooltip()
//});
