'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');
var md = require('js/markdown').full;
var mdQuick = require('js/markdown').quick;



var editor = ace.edit('editor');
var vm = new ViewModel();
var hvm = new hiddenViewModel();
$osf.applyBindings(vm, '#wikiViewRender');
$osf.applyBindings(hvm, '#hidden');
editor.focus();
editor.getSession().setMode('ace/mode/markdown');
editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
editor.getSession().setUseWrapMode(true);   // Wraps text
editor.renderer.setShowGutter(false);       // Hides line number
editor.setShowPrintMargin(false);           // Hides print margin
//editor.setOptions({
//    enableBasicAutocompletion: [LanguageTools.snippetCompleter],
//    enableSnippets: true,
//    enableLiveAutocompletion: true
//});
editor.getSession().on('change', function() {
    updateView(editor.getValue(), vm, hvm);
});
var mdConverter = Markdown.getSanitizingConverter();
var mdEditor = new Markdown.Editor(mdConverter);
mdEditor.run(editor);

function updateView(rawText, vm, hvm){
    //$('#wikiViewRender').html(mdQuick.render(rawText));
    vm.renderedView(mdQuick.render(rawText));
    hvm.currentText(rawText);
}

function ViewModel() {
    var self = this;
    self.renderedView = ko.observable('');
}

function hiddenViewModel() {
    var self = this;
    self.currentText = ko.observable('');
}

$("#Save").onclick = function() {
    alert("test");
};



/**
 * Binding handler that instantiates an ACE editor.
 * The value accessor must be a ko.observable.
 * Example: <div data-bind="ace: currentText" id="editor"></div>
 */

ko.bindingHandlers.mathjaxify = {
    update: function(element, valueAccessor, allBindingsAccessor, data, context) {
        var vm = context.$data;
        //Need to unwrap the data in order for KO to know it's changed.
        ko.unwrap(valueAccessor());

        if(vm.allowMathjaxification() && vm.allowFullRender()) {
            mathrender.mathjaxify('#' + element.id);
        }
    }
};

var editor;
ko.bindingHandlers.ace = {
    init: function (element, valueAccessor) {
        editor = ace.edit('editor');  // jshint ignore: line

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

//var viewModel = {
//    //var self = this;
//    renderedView: ko.observable()
//};
//viewModel.renderedView()

    //self.initText = ko.observable('');
    //self.activeUsers = ko.observableArray([]);
    //self.status = ko.observable('connecting');
    //self.throttledStatus = ko.observable(self.status());
    //
    //self.displayCollaborators = ko.computed(function() {
    //   return self.activeUsers().length > 1;
    //});
    //
    //// Throttle the display when updating status.
    //self.updateStatus = function() {
    //    self.throttledStatus(self.status());
    //};
    //
    //self.throttledUpdateStatus = $osf.throttle(self.updateStatus, 4000, {leading: false});
    //
    //self.status.subscribe(function (newValue) {
    //    if (newValue !== 'connecting') {
    //        self.updateStatus();
    //    }
    //
    //    self.throttledUpdateStatus();
    //});
    //
    //self.statusDisplay = ko.computed(function() {
    //    switch(self.throttledStatus()) {
    //        case 'connected':
    //            return 'Live editing mode';
    //        case 'connecting':
    //            return 'Attempting to connect';
    //        case 'unsupported':
    //            return 'Unsupported browser';
    //        default:
    //            return 'Unavailable: Live editing';
    //    }
    //});
    //
    //self.progressBar = ko.computed(function() {
    //    switch(self.throttledStatus()) {
    //        case 'connected':
    //            return {
    //                class: 'progress-bar progress-bar-success',
    //                style: 'width: 100%'
    //            };
    //
    //        case 'connecting':
    //            return {
    //                class: 'progress-bar progress-bar-warning progress-bar-striped active',
    //                style: 'width: 100%'
    //            };
    //        default:
    //            return {
    //                class: 'progress-bar progress-bar-danger',
    //                style: 'width: 100%'
    //            };
    //    }
    //});
    //
    //self.modalTarget = ko.computed(function() {
    //    switch(self.throttledStatus()) {
    //        case 'connected':
    //            return '#connectedModal';
    //        case 'connecting':
    //            return '#connectingModal';
    //        case 'unsupported':
    //            return '#unsupportedModal';
    //        default:
    //            return '#disconnectedModal';
    //    }
    //});
    //
    //self.wikisDiffer = function(wiki1, wiki2) {
    //    // Handle inconsistencies in newline notation
    //    var clean1 = typeof wiki1 === 'string' ?
    //        wiki1.replace(/(\r\n|\n|\r)/gm, '\n') : '';
    //    var clean2 = typeof wiki2 === 'string' ?
    //        wiki2.replace(/(\r\n|\n|\r)/gm, '\n') : '';
    //
    //    return clean1 !== clean2;
    //};
    //
    //self.changed = function() {
    //    return self.wikisDiffer(self.initText(), self.currentText());
    //};
    //
    //
    //// Revert to last saved version, even if draft is more recent
    //self.revertChanges = function() {
    //    return self.fetchData().then(function(response) {
    //        // Dirty check now covers last saved version
    //        self.initText(response.wiki_content);
    //        self.currentText(response.wiki_content);
    //    });
    //};
    //
    //$(window).on('beforeunload', function() {
    //    if (self.changed() && self.status() !== 'connected') {
    //        return 'There are unsaved changes to your wiki. If you exit ' +
    //            'the page now, those changes may be lost.';
    //    }
    //});

//}
