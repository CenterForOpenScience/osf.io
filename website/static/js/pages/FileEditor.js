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

var EditorViewModel = function(url, viewText) {
    var self = this;

    self.initText = ko.observable('');
    self.url = url;
    self.currentText = viewText; //from filePage's VM
    self.activeUsers = ko.observableArray([]);
    self.status = ko.observable('connecting');
    self.throttledStatus = ko.observable(self.status());

    self.displayCollaborators = ko.computed(function() {
       return self.activeUsers().length > 1;
    });

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
        var className = 'progress-bar progress-bar-width ';
        switch(self.throttledStatus()) {
            case 'connected':
                return {
                    class: className += 'progress-bar-success'
                };
            case 'connecting':
                return {
                    class: className += 'progress-bar-warning progress-bar-striped active'
                };
            default:
                return {
                    class: className += 'progress-bar-danger'
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

    $(window).on('beforeunload', function() {
        if (self.changed() && self.status() !== 'connected') {
            return 'There are unsaved changes to your file. If you exit ' +
                'the page now, those changes may be lost.';
        }
    });
};

EditorViewModel.prototype.updateStatus = function() {
    var self = this;
    self.throttledStatus(self.status());
};

EditorViewModel.prototype.filesDiffer = function(file1, file2) {
    // Handle inconsistencies in newline notation
    var clean1 = typeof file1 === 'string' ?
        file1.replace(/(\r\n|\n|\r)/gm, '\n') : '';
    var clean2 = typeof file2 === 'string' ?
        file2.replace(/(\r\n|\n|\r)/gm, '\n') : '';

    return clean1 !== clean2;
};

EditorViewModel.prototype.changed = function() {
    var self = this;
    return self.filesDiffer(self.initText(), self.currentText());
};

EditorViewModel.prototype.fetchData = function() {
    var self = this;
    var request = $.ajax({
        type: 'GET',
        url: self.url,
    });
    request.done(function (response) {
        self.initText(response);

    });
    request.fail(function (xhr, textStatus, error) {
        $osf.growl('Error','The file content could not be loaded.');
        Raven.captureMessage('Could not GET file contents.', {
            url: self.url,
            textStatus: textStatus,
            error: error
        });
    });
    return request;
};

EditorViewModel.prototype.revertChanges = function() {
    var self = this;
    return self.fetchData().then(function(response) {
        // Dirty check now covers last saved version
        self.initText(response);
        self.currentText(response);
    });
};

function FileEditor(url, viewText, editor) {
    var self = this;
    self.viewModel = new EditorViewModel(url, viewText);
    var mdConverter = Markdown.getSanitizingConverter();
    var mdEditor = new Markdown.Editor(mdConverter);
    mdEditor.run(editor);

}

module.exports = FileEditor;
