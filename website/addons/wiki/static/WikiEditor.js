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
        if (value !== undefined && content !== value) {
            var cursorPosition = editor.getCursorPosition();
            editor.setValue(value);
            editor.gotoLine(cursorPosition.row + 1, cursorPosition.column);
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
            case 'connecting':
                return 'Attempting to Connect';
            case 'noWebSocket':
                return 'Your browser does not support Live Editing';
            default:
                return 'Live Editing Unavailable';
        }
    });

    self.progressBar = ko.computed(function() {
        switch(self.status()) {
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

    self.wikisDiffer = function(wiki1, wiki2) {
        // Handle inconsistencies in newline notation
        var clean1 = typeof wiki1 === 'string' ?
            wiki1.replace(/(\r\n|\n|\r)/gm, '\n') : '';
        var clean2 = typeof wiki2 === 'string' ?
            wiki2.replace(/(\r\n|\n|\r)/gm, '\n') : '';

        return clean1 !== clean2;
    };

    self.changed = function() {
        return self.wikisDiffer(self.publishedText(), self.currentText());
    };

    // Fetch initial wiki text
    self.fetchData = function() {
        var request = $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json'
        });
        request.done(function (response) {
            self.publishedText(response.wiki_content);
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

    self.revertChanges = function() {
        return self.fetchData().then(function() {
            self.currentText(self.publishedText());
        });
    };

    $(window).on('beforeunload', function() {
        if (self.changed() && self.status() !== 'connected') {
            return 'There are unsaved changes to your wiki. If you exit ' +
                'the page now, those changes may be lost.';
        }
    });
}

function WikiEditor(selector, url) {
    this.viewModel = new ViewModel(url);
    $osf.applyBindings(this.viewModel, selector);
    var mdConverter = Markdown.getSanitizingConverter();
    var mdEditor = new Markdown.Editor(mdConverter);
    mdEditor.run(editor);
}

module.exports = WikiEditor;
