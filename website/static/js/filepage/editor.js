var m = require('mithril');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var ShareJSDoc = require('js/pages/ShareJSDocFile.js');
require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports-loader?Markdown=pagedown-ace-converter!pagedown-ace-editor');


var util = require('./util.js');

var model = {};

// This stops the FileEditor Ajax from being called twice on load when
// Mithril reloads the controller twice
var FileFetcher = {
    clear: function(){
        self = this;
        delete self.promise;
    },
    fetch: function(url, reload){
        self = this;
        if(typeof self.promise === 'undefined' || reload){
            self.promise = $.ajax({
                type: 'GET',
                url: url,
                dataType: 'text',
                beforeSend: $osf.setXHRAuthorization,
            });
        }
        return self.promise;
    }
};

var FileEditor = {
    controller: function(contentUrl, shareWSUrl, editorMeta, observables) {
        var self = {};

        self.url = contentUrl;
        self.loaded = false;
        self.initialText = '';
        self.editorMeta = editorMeta;
        self.sharejs_running = true;
        if (typeof sharejs === 'undefined') {
            self.sharejs_running = false;
        }

        self.observables = observables;

        self.unthrottledStatus = self.observables.status;
        $osf.throttle(self.observables.status, 4000, {leading: false});

        self.bindAce = function(element, isInitialized, context) {
            if (isInitialized) {
                return;
            }
            model.editor = ace.edit(element.id);
            model.editor.setValue(self.initialText, -1);
            new ShareJSDoc(shareWSUrl, self.editorMeta, model.editor, self.observables);
        };

        self.loadFile = function(reload) {
            $osf.trackClick('file-page', 'load-file', 'click-revert-file');
            self.loaded = false;
            var response = FileFetcher.fetch(self.url, reload);

            response.done(function (parsed, status, response) {
                m.startComputation();
                self.loaded = true;
                self.initialText = response.responseText;
                if (model.editor) {
                    model.editor.setValue(self.initialText);
                }
                m.endComputation();
            });

            response.fail(function (xhr, textStatus, error) {
                $osf.growl('Error','The file content could not be loaded.');
                Raven.captureMessage('Could not GET file contents.', {
                    extra: {
                        url: self.url,
                        textStatus: textStatus,
                        error: error
                    }
                });
            });
        };

        self.saveFile = $osf.throttle(function() {
            $osf.trackClick('file-page', 'save-file', 'click-save-file');
            var oldstatus = self.observables.status();
            model.editor.setReadOnly(true);
            self.unthrottledStatus('saving');
            m.redraw();
            var request = $.ajax({
                type: 'PUT',
                url: self.url,
                data: model.editor.getValue(),
                beforeSend: $osf.setXHRAuthorization
            }).done(function () {
                FileFetcher.clear();
                model.editor.setReadOnly(false);
                self.unthrottledStatus(oldstatus);
                $(document).trigger('fileviewpage:reload');
                self.initialText = model.editor.getValue();
                m.redraw();
            }).fail(function(xhr, textStatus, err) {
                var message;
                if (xhr.status === 507) {
                    message = 'Could not update file. Insufficient storage space in your Dropbox.';
                } else {
                    message = 'The file could not be updated.';
                }
                model.editor.setReadOnly(false);
                self.unthrottledStatus(oldstatus);
                $(document).trigger('fileviewpage:reload');
                model.editor.setValue(self.initialText);
                $osf.growl('Error', message);
                Raven.captureMessage('Could not PUT file content.', {
                    extra: {
                        textStatus: textStatus,
                        url: self.url
                    }
                });
                m.redraw();
            });
        }, 500);

        self.changed = function() {
            var file1 = self.initialText;
            var file2 = !model.editor ? '' : model.editor.getValue();

            var clean1 = typeof file1 === 'string' ?
                file1.replace(/(\r\n|\n|\r)/gm, '\n') : '';
            var clean2 = typeof file2 === 'string' ?
                file2.replace(/(\r\n|\n|\r)/gm, '\n') : '';

            return clean1 !== clean2;
        };

        self.loadFile(false);

        return self;
    },
    view: function(ctrl) {
        if (!ctrl.loaded || !ctrl.sharejs_running) {
            return util.Spinner;
        }
        return m('.editor-pane.panel-body', [
            m('.wiki-connected-users', m('.row', m('.col-sm-12', [
                m('.ul.list-inline', {style: {'margin-top': '10px'}}, [
                    ctrl.observables.activeUsers().map(function(user) {
                        return m('li', m('a', {href: user.url}, [
                            m('img', {
                                title: user.name,
                                // our shareJS explicitly passes back 'gravatar' despite our generalization
                                src: user.gravatar,
                                'data-container': 'body',
                                'data-placement': 'top',
                                'data-toggle': 'tooltip',
                                style: {border: '1px solid black'}
                            })
                        ]));
                    })

                ])
            ]))),
            m('', {style: {'padding-top': '10px'}}, [
                m('.wmd-input.wiki-editor#editor', {config: ctrl.bindAce})
            ]),
            m('br'),
            m('[style=position:inherit]', [
                m('.row', m('.col-sm-12', [
                    m('.pull-right', [
                        m('button#fileEditorRevert.btn.btn-sm.btn-danger', {onclick: function(){ctrl.loadFile(true);}}, 'Revert'),
                        ' ',
                        m('button#fileEditorSave.btn.btn-sm.btn-success', {onclick: function() {ctrl.saveFile();}}, 'Save')
                    ])
                ]))
            ])
        ]);

    }
};

module.exports = FileEditor;
