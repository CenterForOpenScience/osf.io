'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('osfHelpers');
var Raven = require('raven-js');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');
var md = require('markdown').full;
var md_quick = require('markdown').quick;
var mathrender = require('mathrender');

var editor;

var MATHJAX_THROTTLE = 500;
var throttledMathjaxify = $osf.throttle(mathrender.mathjaxify, MATHJAX_THROTTLE);

/**
 * Binding handler that instantiates an ACE editor.
 * The value accessor must be a ko.observable.
 * Example: <div data-bind="ace: currentText" id="editor"></div>
 */
ko.bindingHandlers.ace = {
    init: function (element, valueAccessor) {
        editor = ace.edit(element.id); // jshint ignore:line

        // Updates the view model based on changes to the editor
        editor.getSession().on('change', function () {
            valueAccessor()(editor.getValue());
        });
    },
    update: function (element, valueAccessor) {
        var content = editor.getValue();        // Content of ace editor
        var value = ko.unwrap(valueAccessor()); // Value from view model

        // Updates the editor based on changes to the view model
        if (value !== undefined && content !== value) {
            var cursorPosition = editor.getCursorPosition();
            editor.setValue(value);
            editor.gotoLine(cursorPosition.row + 1, cursorPosition.column);
        }
    }
};

function ViewModel(url) {
    var self = this;

    self.initText = ko.observable('');
    self.currentText = ko.observable('');
    self.activeUsers = ko.observableArray([]);
    self.status = ko.observable('connected');
    self.throttledStatus = ko.observable(self.status());

    self.displayCollaborators = ko.computed(function() {
       return self.activeUsers().length > 1;
    });

    // Throttle the display when updating status.
    self.updateStatus = function() {
        self.throttledStatus(self.status());
    };

    self.throttledUpdateStatus = $osf.throttle(self.updateStatus, 4000, {leading: false});

    self.status.subscribe(function (newValue) {
        if (newValue === 'disconnected') {
            self.updateStatus();
        }

        self.throttledUpdateStatus();
    });

    self.statusDisplay = ko.computed(function() {
        switch(self.throttledStatus()) {
            case 'connecting':
                return 'Attempting to connect';
            case 'unsupported':
                return 'Your browser does not support live editing';
            default:
                return 'Live editing unavailable';
        }
    });

    self.progressBar = ko.computed(function() {
        switch(self.throttledStatus()) {
            case 'connecting':
                return {
                    class: 'progress-bar progress-bar-warning progress-bar-striped active',
                    style: 'width: 100%'
                };
            default:
                return {
                    class: 'progress-bar progress-bar-danger',
                    style: 'width: 100%'
                };
        }
    });

    self.modalTarget = ko.computed(function() {
        switch(self.throttledStatus()) {
            case 'connecting':
                return '#connectingModal';
            case 'unsupported':
                return '#unsupportedModal';
            default:
                return '#disconnectedModal';
        }
    });

    self.wikisDiffer = function(wiki1, wiki2) {
        // Handle inconsistencies in newline notation
        var clean1 = typeof wiki1 === 'string' ?
            wiki1.replace(/(\r\n|\n|\r)/gm, '\n') : '';
        var clean2 = typeof wiki2 === 'string' ?
            wiki2.replace(/(\r\n|\n|\r)/gm, '\n') : '';

        return clean1 !== clean2;
    };

    self.changed = function() {
        return self.wikisDiffer(self.initText(), self.currentText());
    };

    // Fetch initial wiki text
    self.fetchData = function() {
        var request = $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json'
        });
        request.done(function (response) {
            // Most recent version, whether saved or in mongo
            self.initText(response.wiki_draft);
        });
        request.fail(function (xhr, textStatus, error) {
            $osf.growl('Error','The wiki content could not be loaded.');
            Raven.captureMessage('Could not GET wiki contents.', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
        return request;
    };

    // Revert to last saved version, even if draft is more recent
    self.revertChanges = function() {
        return self.fetchData().then(function(response) {
            // Dirty check now covers last saved version
            self.initText(response.wiki_content);
            self.currentText(response.wiki_content);
        });
    };

    $(window).on('beforeunload', function() {
        if (self.changed() && self.status() !== 'connected') {
            return 'There are unsaved changes to your wiki. If you exit ' +
                'the page now, those changes may be lost.';
        }
    });

    $(document).ready(function () {
        $('*[data-osf-panel]').osfPanel({
            buttonElement : '.switch',
            onSize : 'md',
            'onclick' : function () { editor.resize(); }
        });
        $('.openNewWiki').click(function () {
            $('#newWiki').modal('show');
        });
        $('.openDeleteWiki').click(function () {
            $('#deleteWiki').modal('show');
        });
        var panelToggle = $('.panel-toggle'),
            panelExpand = $('.panel-expand');
        $('.panel-collapse').on('click', function () {
            var el = $(this).closest('.panel-toggle');
            el.children('.wiki-panel.hidden-xs').hide(  );
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

    });
}

function WikiEditor(selector, url) {
    this.viewModel = new ViewModel(url);
    $osf.applyBindings(this.viewModel, selector);
    var mdConverter = Markdown.getSanitizingConverter();
    var mdEditor = new Markdown.Editor(mdConverter);
    mdEditor.run(editor);
    var previewElement = $('#markdownItPreview');
    var renderTimeout;
    editor.on('change', function() {
        // Quick render
        previewElement.html(md_quick.render(editor.getValue()));
        // Full render
        clearTimeout(renderTimeout);
        renderTimeout = setTimeout(function() {
            previewElement.html(md.render(editor.getValue()));
            throttledMathjaxify('#markdownItPreview');
        }, 500);
    });
}

module.exports = WikiEditor;
