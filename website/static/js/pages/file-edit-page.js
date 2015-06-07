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

var editable = (ctx.panelsUsed.indexOf('edit') !== -1);
var viewable = (ctx.panelsUsed.indexOf('view') !== -1);

var filePageOptions = {
    editVisible: editable,
    viewVisible: viewable,
    canEdit: ctx.canEdit,
    isEditable: ctx.isEditable,
    urls: ctx.urls,
    metadata: ctx.metadata
};

var filePage = new FilePage('#filePageContext', filePageOptions);

// Apply panels
$(document).ready(function () {
    var bodyElement = $('body');

    $('*[data-osf-panel]').osfPanel({
        buttonElement : '.switch',
        onSize : 'xs',
        onclick : function (event, title, buttonState, thisbtn, col) {
            // this = all the column elements; an array
            // title = Text of the button
            // buttonState = the visibility of column after click, taken from data-osf-toggle attribute,
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

            ace.edit(editor).resize();  // jshint ignore: line
        }
    });
});
