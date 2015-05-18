'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');


/**
 * Binding handler that instantiates an ACE editor.
 * The value accessor must be a ko.observable.
 * Example: <div data-bind="ace: currentText" id="editor"></div>
 */
var editor;
ko.bindingHandlers.ace = {
    init: function (element, valueAccessor) {
        editor = ace.edit(element.id);  // jshint ignore: line

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

function ViewModel(url, viewText) {
    var self = this;

    self.initText = ko.observable('');
    self.currentText = viewText; //from filePage's VM
    self.activeUsers = ko.observableArray([]);
    self.status = ko.observable('connecting');
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
        if (newValue !== 'connecting') {
            self.updateStatus();
        }

        self.throttledUpdateStatus();
    });

    self.statusDisplay = ko.computed(function() {
        switch(self.throttledStatus()) {
            case 'connected':
                return 'Live editing mode';
            case 'connecting':
                return 'Attempting to connect';
            case 'unsupported':
                return 'Unsupported browser';
            default:
                return 'Unavailable: Live editing';
        }
    });

    self.progressBar = ko.computed(function() {
        switch(self.throttledStatus()) {
            case 'connected':
                return {
                    class: 'progress-bar progress-bar-success',
                    style: 'width: 100%'
                };

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
            case 'connected':
                return '#connectedModal';
            case 'connecting':
                return '#connectingModal';
            case 'unsupported':
                return '#unsupportedModal';
            default:
                return '#disconnectedModal';
        }
    });

    self.filesDiffer = function(file1, file2) {
        // Handle inconsistencies in newline notation
        var clean1 = typeof wiki1 === 'string' ?
            file1.replace(/(\r\n|\n|\r)/gm, '\n') : '';
        var clean2 = typeof wiki2 === 'string' ?
            file2.replace(/(\r\n|\n|\r)/gm, '\n') : '';

        return clean1 !== clean2;
    };

    self.changed = function() {
        return self.filesDiffer(self.initText(), self.currentText());
    };

    // Fetch initial file text
    self.fetchData = function() {
        var request = $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json'
        });
        request.done(function (response) {
            self.initText(response.content);

        });
        request.fail(function (xhr, textStatus, error) {
            $osf.growl('Error','The file content could not be loaded.');
            Raven.captureMessage('Could not GET file contents.', {
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
            self.initText(response.content);
            self.currentText(response.content);
        });
    };

    $(window).on('beforeunload', function() {
        if (self.changed() && self.status() !== 'connected') {
            return 'There are unsaved changes to your wiki. If you exit ' +
                'the page now, those changes may be lost.';
        }
    });

}

function FileEditor(url, viewText, editor) {
    this.viewModel = new ViewModel(url, viewText);
    var mdConverter = Markdown.getSanitizingConverter();
    var mdEditor = new Markdown.Editor(mdConverter);
    mdEditor.run(editor);

}

module.exports = FileEditor;
