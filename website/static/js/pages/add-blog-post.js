'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var waterbutler = require('js/waterbutler');
require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');
var md = require('js/markdown').full;
var mdQuick = require('js/markdown').quick;



var editor = ace.edit('editor');
var form = new formViewModel();
var save = function () {
    var title = $("input[name='title']").val();
    var content = $("#hidden").val();
    var ctx = window.contextVars;
    var uid = ctx.uid;
    var guid = ctx.guid;
    var path = '/' + ctx.node.path + '/';
    var name = ctx.file.name;
    var date = getDate();
    var header = createHeader(title, uid, name, date);
    var fileName = name + ".md";
    var b = new Blob([header + content], {type: "text/plain", lastModified: date});
    var xhr = new XMLHttpRequest();
    var f = new File(b, fileName, xhr);
    var url = waterbutler.buildUploadUrl(path, 'osfstorage', guid, f);

    xhr.open("put", url, true);
    xhr = $osf.setXHRAuthorization(xhr);
    xhr.send(f);
    window.location = "../post/" + name;
};
form.save = save;
$osf.applyBindings(form, '#wiki-form');
editor.focus();
editor.getSession().setMode('ace/mode/markdown');
editor.getSession().setUseSoftTabs(true);   // Replace tabs with spaces
editor.getSession().setUseWrapMode(true);   // Wraps text
editor.renderer.setShowGutter(false);       // Hides line number
editor.setShowPrintMargin(false);           // Hides print margin
editor.getSession().on('change', function() {
    updateView(editor.getValue(), form);
});
var mdConverter = Markdown.getSanitizingConverter();
var mdEditor = new Markdown.Editor(mdConverter);
mdEditor.run(editor);

function updateView(rawText, form){
    form.renderedView(mdQuick.render(rawText));
    form.currentText(rawText);
}

function formViewModel() {
    var self = this;
    self.save = ko.observable('');
    self.currentText = ko.observable('');
    self.renderedView = ko.observable('');
}


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

function createHeader(title, uid, name, date) {
    var start = "/**\n";
    date  = "date: " + date + "\n";
    var author = "author: " + uid + "\n";
    title = "title: " + title + "\n";
    var post_class = "post_class: post\n";
    var file = "file: " + name + "\n";
    var end = "**/\n";
    return start + date + author + title + post_class + file + end;
};

function getDate() {
    var today = new Date();
    var dd = today.getDate();
    var mm = today.getMonth() + 1;
    var yyyy = today.getFullYear();

    if(dd<10) {
        dd='0'+dd;
    }

    if(mm<10) {
        mm='0'+mm;
    }

    return yyyy + "-" + mm + "-" + dd;
};

function File(blob, name, xhr){
    var self = blob;
    self.name = name;
    self.xhr = xhr;
    return self;
}
