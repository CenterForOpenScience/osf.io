var m = require('mithril');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');
require('ace-noconflict');
require('ace-mode-markdown');
require('ace-ext-language_tools');
require('addons/wiki/static/ace-markdown-snippets.js');


var util = require('./util.js');

var FileEditor = {
    controller: function(contentUrl) {
        var self = this;
        self.url = contentUrl;
        self.loaded = false;
        self.initialText = '';
        self.editor = undefined;

        self.bindAce = function(element, isInitialized, context) {
            if (isInitialized) return;
            self.editor = ace.edit(element.id);
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

        self.reloadFile();
    },
    view: function(ctrl) {
        if (!ctrl.loaded) return util.Spinner;

        return m('.editor-pane', [
            m('.editor', {config: ctrl.bindAce}),
            m('.panel', [
                m('button.btn.btn-danger', 'Revert'),
                m('button.btn.btn-danger', 'Save')
            ])
        ]);

    }
};

module.exports = FileEditor;



///    <div class="panel-expand col-md-6">
///            <div class="wiki" id="filePageContext">
///                <div data-bind="with: $root.editVM.fileEditor.viewModel" data-osf-panel="Edit" style="display: none">
///                    <div class="osf-panel" >
///                        <div class="osf-panel-header" >
///                            <div class="wiki-panel">
///                                <div class="wiki-panel-header">
///                                    <div class="row">
///                                        <div class="col-md-6">
///                                            <span class="wiki-panel-title" > <i class="fa fa-pencil-square-o"></i>   Edit </span>
///                                        </div>
///                                        <div class="col-md-6">
///                                            <div class="pull-right">
///                                                <div class="progress progress-no-margin pointer " data-toggle="modal" data-bind="attr: {data-target: modalTarget}" >
///                                                    <div role="progressbar" data-bind="attr: progressBar">
///                                                        <span class="progress-bar-content">
///                                                            <span data-bind="text: statusDisplay"></span>
///                                                            <span class="sharejs-info-btn">
///                                                                <i class="fa fa-question-circle fa-large"></i>
///                                                            </span>
///                                                        </span>
///                                                    </div>
///                                                </div>
///                                            </div>
///                                        </div>
///                                    </div>
///                                </div>
///                            </div>
///                        </div>

///                        <form id="file-edit-form">
///                            <div class="wiki-panel-body" style="padding: 10px">
///                                <div class="row">
///                                    <div class="col-xs-12">
///                                        <div class="form-group wmd-panel">
///                                            <ul class="list-inline" data-bind="foreach: activeUsers" class="pull-right">
///                                              {{#ifnot: id === '${user['id']}'}}
///                                                  <li><a data-bind="attr: { href: url }" >
///                                                      <img data-container="body" data-bind="attr: {src: gravatar}, tooltip: {title: name, placement: 'top'}"
///                                                           style="border: 1px solid black;">
///                                                  </a></li>
///                                              {{/ifnot}}
///                                            </ul>
///                                            <div id="wmd-button-bar" style="display: none"></div>
///                                            <div id="editor" class="wmd-input wiki-editor" data-bind="ace: currentText">Loading. . .</div>
///                                        </div>
///                                    </div>
///                                </div>
///                            </div>

///                            <div class="wiki-panel-footer">
///                                <div class="row">
///                                    <div class="col-xs-12">
///                                        <div class="pull-right">
///                                            <button id="revert-button" class="btn btn-danger" data-bind="click: revertChanges, enable: changed()">Revert</button>
///                                            <button id="save-button" class="btn btn-success" data-bind="click: saveChanges, enable: changed()">Save</button>
///                                        </div>
///                                    </div>
///                                </div>

///                                <!-- Invisible textarea for form submission -->
///                                <textarea id="original_content" style="display: none;"></textarea>
///                                <textarea id="edit_content" style="display: none;" data-bind="value: currentText"></textarea>

///                            </div>
///                        </form>
///                    </div>
///                </div>
///            </div>
