/**
* Initializes the pagedown editor and prompts the user if
* leaving the page with unsaved changes.
*/
'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('osfHelpers');
var Raven = require('raven-js');
require('bootstrap-editable');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');

var editor;

ko.bindingHandlers.ace = {
    init: function(element, valueAccessor) {
        editor = ace.edit(element.id);

        // Updates the view model based on changes to the editor
        editor.getSession().on('change', function () {
            valueAccessor()(editor.getValue());
        });
    },
    update: function (element, valueAccessor) {
        var content = editor.getValue();        // Content of ace editor
        var value = ko.unwrap(valueAccessor()); // Value from view model

        // Updates the editor based on changes to the view model
        if (!editor.getReadOnly() && value !== undefined && content !== value) {
            editor.setValue(value, -1);
        }
    }
};

function ViewModel(url) {
    var self = this;

    self.publishedText = ko.observable('');
    self.currentText = ko.observable('');
    self.activeUsers = ko.observableArray([]);
    self.status = ko.observable('connecting');

    self.displayCollaborators = ko.computed(function() {
       return self.activeUsers().length > 1;
    });

    self.statusDisplay = ko.computed(function() {
        switch(self.status()) {
            case 'connected':
                return 'Live Editing Mode';
            case 'connecting':
                return 'Attempting to Reconnect';
            default:
                return 'Live Editing Unavailable';
        }
    });

    self.progressBar = ko.computed(function() {
        switch(self.status()) {
            case 'connected':
                return {
                    class: "progress-bar progress-bar-success",
                    style: "width: 100%"
                };
            case 'connecting':
                return {
                    class: "progress-bar progress-bar-warning progress-bar-striped active",
                    style: "width: 100%"
                };
            default:
                return {
                    class: "progress-bar progress-bar-danger",
                    style: "width: 100%"
                };
        }
    });

    self.modalTarget = ko.computed(function() {
        switch(self.status()) {
            case 'connected':
                return '#connected-modal';
            case 'connecting':
                return '#connecting-modal';
            default:
                return '#disconnected-modal';
        }
    });

    self.changed = function() {
        // Handle inconsistencies in newline notation
        var published = typeof self.publishedText() === 'string' ?
            self.publishedText().replace(/(\r\n|\n|\r)/gm, '\n') : '';
        var current = typeof self.currentText() === 'string' ?
            self.currentText().replace(/(\r\n|\n|\r)/gm, '\n') : '';

        return published !== current;
    };

    // Fetch initial wiki text
    self.fetchData = function(callback) {
        $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json',
            success: function (response) {
                self.publishedText(response.wiki_content);
                if (callback) callback(response);
            },
            error: function (xhr, textStatus, error) {
                $.osf.growl('Error','The wiki content could not be loaded.');
                Raven.captureMessage('Could not GET wiki contents.', {
                    url: url,
                    textStatus: textStatus,
                    error: error
                });
            }
        });
    };

    self.loadPublished = function() {
        self.fetchData(function() {
            self.currentText(self.publishedText());
        });
    };

    self.fetchData();

    $(window).on('beforeunload', function() {
        if (self.changed() && self.status() !== 'connected') {
            return 'There are unsaved changes to your wiki.';
        }
    });
}

function WikiEditor(selector, url) {
    this.viewModel = new ViewModel(url);
    $.osf.applyBindings(this.viewModel, selector);
    var mdConverter = Markdown.getSanitizingConverter();
    var mdEditor = new Markdown.Editor(mdConverter);
    mdEditor.run(editor);
}

module.exports = WikiEditor;
