'use strict';

var $ = require('jquery');
require('bootstrap-editable');
require('osf-panel');
var FilePage = require('filePage');

require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');

var $osf = require('js/osfHelpers');

var FileRenderer = require('../filerenderer.js');
var FileRevisions = require('../fileRevisions.js');


var ctx = window.contextVars;  // mako context variables

var editable = (ctx.panelsUsed.indexOf('edit') !== -1);
var viewable = (ctx.panelsUsed.indexOf('view') !== -1);

var filePageOptions = {
    editVisible: true,
    viewVisible: true,
    canEdit: ctx.currentUser.canEdit,
    isEditable: true,
    // isEditable: ctx.isEditable,
    urls: ctx.file.urls,
    metadata: ctx.editor
};


// Apply panels
$(document).ready(function () {
    var renderer;
    var filePage;
    var bodyElement = $('body');

    new FileRevisions(
        '#fileRevisions',
        window.contextVars.node,
        window.contextVars.file,
        window.contextVars.currentUser.canEdit
    );

    if (window.contextVars.file.urls.render !== undefined) {
        renderer = new FileRenderer(window.contextVars.file.urls.render, '#fileRendered');
        renderer.start();
    }

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

            if (filePage === undefined) {
                filePage =new FilePage('#filePageContext', filePageOptions, renderer);
            }

            ace.edit(editor).resize();  // jshint ignore: line
        }
    });
});
