/**
* Initializes the pagedown editor and prompts the user if
* leaving the page with unsaved changes.
*/
'use strict';
// TODO: Use commonjs+webpack to load pagedown modules
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('osfHelpers');
var Raven = require('raven-js');
require('bootstrap-editable');

var editor;
var preview;

ko.bindingHandlers.ace = {
    init: function(element, valueAccessor) {
        editor = ace.edit(element.id);
        preview = $('#' + element.id + '-preview');

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
            editor.setValue(value);
        }
    }
};

ko.bindingHandlers.tooltip = {
    init: function(element, valueAccessor) {
        var value = ko.unwrap(valueAccessor());
        var options = {
            title: value,
            placement: 'bottom'
        };

        $(element).tooltip(options);
    }
};

function ViewModel(url) {
    var self = this;

    self.publishedText = ko.observable('');
    self.currentText = ko.observable('');
    self.activeUsers = ko.observableArray([]);

    self.displayCollaborators = ko.computed(function() {
       return self.activeUsers().length > 1;
    });

    self.changed = ko.computed(function() {
        // Handle inconsistencies in newline notation
        var published = typeof self.publishedText() === 'string' ?
            self.publishedText().replace(/(\r\n|\n|\r)/gm, '\n') : '';
        var current = typeof self.currentText() === 'string' ?
            self.currentText().replace(/(\r\n|\n|\r)/gm, '\n') : '';

        return published !== current;
    });

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

    // TODO: Do we want this?
//        $(window).on('beforeunload', function() {
//            if (self.changed()) {
//                return 'If you leave this page, your changes will be ' +
//                    'saved as a draft for collaborators, but not made public.';
//            }
//        });
}

function WikiEditor(selector, url) {
    this.viewModel = new ViewModel(url);
    $.osf.applyBindings(this.viewModel, selector);
    var mdConverter = Markdown.getSanitizingConverter();
    var mdEditor = new Markdown.Editor(mdConverter);
    mdEditor.run(editor);

    // The automatic converter has an issue with automatic page scrolling
    editor.getSession().on('change', function () {
        preview.html(mdConverter.makeHtml(editor.getValue()));
    });
}

module.exports = WikiEditor;
