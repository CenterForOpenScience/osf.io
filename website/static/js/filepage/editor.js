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
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');


var util = require('./util.js');

var FileEditor = {
    controller: function(contentUrl, shareWSUrl, editorMeta, observables) {
        var self = this;
        self.url = contentUrl;
        self.loaded = false;
        self.initialText = '';
        self.editor = undefined;
        self.editorMeta = editorMeta;
        self.changed = m.prop(false);

        self.observables = observables;

        $osf.throttle(self.observables.status, 4000, {leading: false});

        self.bindAce = function(element, isInitialized, context) {
            if (isInitialized) return;
            self.editor = ace.edit(element.id);
            self.editor.setValue(self.initialText);
            self.editor.on('change', self.onChanged);
            new ShareJSDoc(shareWSUrl, self.editorMeta, self.editor, self.observables);
        };

        self.reloadFile = function() {
            self.loaded = false;
            $.ajax({
                type: 'GET',
                url: self.url,
                beforeSend: $osf.setXHRAuthorization,
                dataType: 'text',
                mimeType: 'text/plain; charset=x-user-defined'
            }).done(function (parsed, status, response) {
                m.startComputation();
                self.loaded = true;
                self.initialText = response.responseText;
                if (self.editor) {
                    self.editor.setValue(self.initialText);
                }
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

        //Really crappy hack, panel and m.component blackbox this module
        //so its not possible, in the alotted time, to bind a function here to
        //buttons ~2 levels up
        $(document).on('fileviewpage:save', function() {
            if(self.changed()) {
                var oldstatus = self.observables.status();
                self.editor.setReadOnly(true);
                self.observables.status('saving');
                m.redraw();
                var request = $.ajax({
                    type: 'PUT',
                    url: self.url,
                    data: self.editor.getValue(),
                    beforeSend: $osf.setXHRAuthorization
                }).done(function () {
                    self.editor.setReadOnly(false);
                    self.observables.status(oldstatus);
                    $(document).trigger('fileviewpage:reload');
                    self.initialText = self.editor.getValue();
                    m.redraw();
                }).fail(function(error) {
                    self.editor.setReadOnly(false);
                    self.observables.status(oldstatus);
                    $(document).trigger('fileviewpage:reload');
                    self.editor.setValue(self.initialText);
                    $osf.growl('Error', 'The file could not be updated.');
                    Raven.captureMessage('Could not PUT file content.', {
                        error: error,
                        url: self.url
                    });
                    m.redraw();
                });
            } else {
                alert('There are no changes to save.');
            }
        });

        //See Above comment
        $(document).on('fileviewpage:revert', function() {
            self.reloadFile();
        });

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
            m('.wiki-connected-users', m('.row', m('.col-md-12', [
                m('.ul.list-inline', {style: {'margin-top': '10px'}}, [
                    ctrl.observables.activeUsers().map(function(user) {
                        return m('li', m('a', {href: user.url}, [
                            m('img', {
                                title: user.name,
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
        ]);

    }
};

module.exports = FileEditor;
