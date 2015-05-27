var m = require('mithril');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');


var util = require('./util.js');

var FileEditor = {
    controller: function(contentUrl, shareWSUrl, editorMeta, triggerReload) {
        var self = this;
        self.url = contentUrl;
        self.loaded = false;
        self.initialText = '';
        self.editor = undefined;
        self.editorMeta = editorMeta;
        self.triggerReload = triggerReload;
        self.changed = m.prop(false);

        self.bindAce = function(element, isInitialized, context) {
            if (isInitialized) return;
            self.editor = ace.edit(element.id);
            self.editor.setValue(self.initialText);
            self.editor.on('change', self.onChanged);
            // var ShareJSDoc = require('js/pages/ShareJSDocFile.js');
            // new ShareJSDoc(self.contentURL, self.editorMetadata, self.editor);
        };

        self.reloadFile = function() {
            self.loaded = false;
            $.ajax({
                type: 'GET',
                url: self.url,
                beforeSend: $osf.setXHRAuthorization
            }).done(function (response) {
                m.startComputation();
                self.loaded = true;
                self.initialText = response;
                m.endComputation();
            }).fail(function (xhr, textStatus, error) {
                $osf.growl('Error','The file content could not be loaded.');
                Raven.captureMessage('Could not GET file contents.', {
                    url: self.url,
                    textStatus: textStatus,
                    error: error
                });
            });
        };

        self.saveChanges = function() {
            var request = $.ajax({
                type: 'PUT',
                url: self.url,
                data: self.editor.getValue(),
                beforeSend: $osf.setXHRAuthorization
            }).done(function () {
                self.triggerReload();
                self.initText = self.editor.getValue();
            }).fail(function(error) {
                self.editor.setValue(self.initialText);
                $osf.growl('Error', 'The file could not be updated.');
                Raven.captureMessage('Could not PUT file content.', {
                    error: error,
                    url: self.url,
                });
            });
        };

        self.revertChanges = function() {
            self.reloadFile();
        };

        self.onChanged = function(e) {
            //To avoid extra typing
            var file1 = self.initialText;
            var file2 = !self.editor ? '' : self.editor.getValue();

            var clean1 = typeof file1 === 'string' ?
                file1.replace(/(\r\n|\n|\r)/gm, '\n') : '';
            var clean2 = typeof file2 === 'string' ?
                file2.replace(/(\r\n|\n|\r)/gm, '\n') : '';

            self.changed(clean1 !== clean2);
        };

        self.reloadFile();
    },
    view: function(ctrl) {
        if (!ctrl.loaded) return util.Spinner;

        return m('.editor-pane', [
            m('.wmd-input.wiki-editor#editor', {config: ctrl.bindAce}),
            m('.osf-panel-footer', [
                m('.col-xs-12', [
                    m('.pull-right', [
                        // m('button.btn.btn-danger', {onclick: ctrl.revertChanges, disabled: ctrl.changed() ? '' : 'disabled'}, 'Revert'),
                        // m('button.btn.btn-success', {onclick: ctrl.saveChanges, disabled: ctrl.changed() ? '' : 'disabled'}, 'Save')
                        m('button.btn.btn-danger', {onclick: ctrl.revertChanges}, 'Revert'),
                        m('button.btn.btn-success', {onclick: ctrl.saveChanges}, 'Save')
                    ])
                ])
            ])
        ]);

    }
};

module.exports = FileEditor;
