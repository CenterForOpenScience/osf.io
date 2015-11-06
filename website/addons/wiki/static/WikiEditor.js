'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var Markdown = require('pagedown-ace-converter');
Markdown.getSanitizingConverter = require('pagedown-ace-sanitizer').getSanitizingConverter;
require('imports?Markdown=pagedown-ace-converter!pagedown-ace-editor');

var waterbutler = require('js/waterbutler');


/**
 * Binding handler that instantiates an ACE editor.
 * The value accessor must be a ko.observable.
 * Example: <div data-bind="ace: currentText" id="editor"></div>
 */
var editor;

ko.bindingHandlers.ace = {
    init: function (element, valueAccessor) {
        editor = ace.edit(element.id);  // jshint ignore: line
        editor.renderer.setShowGutter(true);
        editor.renderer.setOption('showLineNumbers', true);

        editor.getPosition = function(x, y) {

            var config = editor.renderer.$markerFront.config;
            var height = config.lineHeight;
            var width = config.characterWidth;
            var row = Math.floor(y/height) < editor.session.getScreenLength() ? Math.floor(y/height) : editor.session.getScreenLength() - 1;
            var column = Math.floor(x/width) < editor.session.getScreenLastRowColumn(row) ? Math.floor(x/width) : editor.session.getScreenLastRowColumn(row);
            return {row: row, column: column}

        };
        // Updates the view model based on changes to the editor
        editor.getSession().on('change', function () {
            valueAccessor()(editor.getValue());
        });

        editor.marker = {};
        editor.marker.cursor = {};
        editor.marker.active = false;
        editor.marker.update = function(html, markerLayer, session, config) {
            var height = config.lineHeight;
            var width = config.characterWidth;
            var top = markerLayer.$getTop(this.cursor.row, config);
            var left = markerLayer.$padding + this.cursor.column * width;
            html.push(
                '<div class=\'drag-drop-cursor\' style=\'',
                'height:', height, 'px;',
                'top:', top, 'px;',
                'left:', left, 'px; width:', width, 'px\'></div>'
            );
        };

        editor.marker.redraw = function() {
            this.session._signal("changeFrontMarker");
        };

        element.addEventListener('dragenter', function(event) {
            event.preventDefault();
            event.stopPropagation();
        }, false);

        element.addEventListener('dragover', function(event) {
            event.preventDefault();
            event.stopPropagation();
            if (!editor.marker.active) {
                editor.marker.active = true;
                editor.marker.session = editor.session;
                editor.marker.session.addDynamicMarker(editor.marker, true);
            }
            editor.marker.cursor = editor.getPosition(event.offsetX, event.offsetY);
            editor.marker.redraw();
            var effect;
                try {
                  effect = event.dataTransfer.effectAllowed;
                } catch (_error) {}
                event.dataTransfer.dropEffect = 'move' === effect || 'linkMove' === effect ? 'move' : 'copy';
        }, false);

        element.addEventListener('drop', function(event) {
            event.preventDefault();
            event.stopPropagation();
            var re = /(?:\.([^.]+))?$/;
            var extensions = ['jpg', 'png', 'gif', 'bmp'];
            var ext;
            var position = editor.session.screenToDocumentPosition(editor.marker.cursor.row, editor.marker.cursor.column);
            var url = event.dataTransfer.getData('text/html');
            if (!!url) {
                var getImage = /(src=")(.*?)(")/;
                var imgURL = getImage.exec(url)[2];
                if (imgURL.substring(0,10) === 'data:image') {
                    imgURL = event.dataTransfer.getData('URL');
                    var exp = /(imgurl=)(.*?)(&)/;
                    if (!!exp.exec(imgURL)) {
                        imgURL = exp.exec(imgURL)[2];
                    }
                    else {
                        //alert('cant do this');
                        $osf.growl('Error', 'Please find a prettier URL to give us or download to your computer and drop it in from there');
                        imgURL = undefined;
                    }

                }
                else {
                    ext = re.exec(imgURL)[1];
                    if (extensions.indexOf(ext) <= -1) {
                        $osf.growl('Error', 'File type not supported', 'danger');
                        imgURL = undefined;
                    }
                }
                if (!!imgURL) {
                    var refOut = editor.marker.addLinkDef('[999]: ' + imgURL);
                    editor.session.insert(position, '![enter image description here][' + refOut + ']');
                }
            }
            else {
                var file = event.dataTransfer.files[0];
                ext = re.exec(file.name)[1];
                if (extensions.indexOf(ext) <= -1) {
                    $osf.growl('Error', 'File type not supported', 'danger');
                }
                else {
                    var waterbutler_url = waterbutler.buildUploadUrl('/', 'osfstorage', window.contextVars.node.id, file);
                    $.ajax({
                        url: waterbutler_url,
                        type: 'PUT',
                        processData: false,
                        contentType: false,
                        beforeSend: $osf.setXHRAuthorization,
                        data: file
                    }).done(function(data) {
                        //url = waterbutler.buildDownloadUrl(data.path, data.provider, window.contextVars.node.id, {mode: 'render'});
                        url = window.contextVars.waterbutlerURL + 'v1/resources/' + window.contextVars.node.id + '/providers/' + data.provider + data.path + '?mode=render';
                        var refOut = editor.marker.addLinkDef('[999]: ' + url);
                        editor.session.insert(position, '![enter image description here][' + refOut + ']');
                    }).fail(function(data) {
                        $osf.growl('Error', 'File not uploaded. Please refresh the page and try ' +
                        'again or contact <a href="mailto: support@cos.io">support@cos.io</a> ' +
                        'if the problem persists.', 'danger');
                    });
                }
            }
            editor.marker.session.removeMarker(editor.marker.id);
            editor.marker.redraw();
            editor.marker.active = false;
        }, false);

        element.addEventListener('dragleave', function(event) {
            event.preventDefault();
            event.stopPropagation();
            editor.marker.session.removeMarker(editor.marker.id);
            editor.marker.redraw();
            editor.marker.active = false;
        });

        editor.marker.addLinkDef = function(linkDef) {
            var Range = ace.require('ace/range').Range;
            var before = editor.session.getTextRange(new Range(0, 0, this.cursor.row, this.cursor.column));
            var after = editor.session.getTextRange(new Range(this.cursor.row, this.cursor.column, Number.MAX_VALUE, Number.MAX_VALUE));
            var refNumber = 0; // The current reference number
            var defsToAdd = {}; //
            // Start with a clean slate by removing all previous link definitions.
            before = this.stripLinkDefs(before, defsToAdd);
            after = this.stripLinkDefs(after, defsToAdd);

            var defs = "";
            var regex = /(\[)((?:\[[^\]]*\]|[^\[\]])*)(\][ ]?(?:\n[ ]*)?\[)(\d+)(\])/g;

            var addDefNumber = function (def) {
                refNumber++;
                def = def.replace(/^[ ]{0,3}\[(\d+)\]:/, "  [" + refNumber + "]:");
                defs += "\n" + def;
            };

            // note that
            // a) the recursive call to getLink cannot go infinite, because by definition
            //    of regex, inner is always a proper substring of wholeMatch, and
            // b) more than one level of nesting is neither supported by the regex
            //    nor making a lot of sense (the only use case for nesting is a linked image)
            var getLink = function (wholeMatch, before, inner, afterInner, id, end) {
                inner = inner.replace(regex, getLink);
                if (defsToAdd[id]) {
                    addDefNumber(defsToAdd[id]);
                    return before + inner + afterInner + refNumber + end;
                }
                return wholeMatch;
            };

            before = before.replace(regex, getLink);

            if (linkDef) {
                addDefNumber(linkDef);
                var refOut = refNumber;
            }

            after = after.replace(regex, getLink);

            if (after) {
                after = after.replace(/\n*$/, "");
            }

            after += "\n\n" + defs;

            editor.setValue(before + after);

            return refOut;
        };

        editor.marker.stripLinkDefs = function (text, defsToAdd) {

            text = text.replace(/^[ ]{0,3}\[(\d+)\]:[ \t]*\n?[ \t]*<?(\S+?)>?[ \t]*\n?[ \t]*(?:(\n*)["(](.+?)[")][ \t]*)?(?:\n+|$)/gm,
                function (totalMatch, id, link, newlines, title) {
                    defsToAdd[id] = totalMatch.replace(/\s*$/, "");
                    if (newlines) {
                        // Strip the title and return that separately.
                        defsToAdd[id] = totalMatch.replace(/["(](.+?)[")]$/, "");
                        return newlines + title;
                    }
                    return "";
                });

            return text
        }
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
    self.currentText = viewText; //from wikiPage's VM
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

    self.wikisDiffer = function(wiki1, wiki2) {
        // Handle inconsistencies in newline notation
        var clean1 = typeof wiki1 === 'string' ? 
            wiki1.replace(/(\r\n|\n|\r)/gm, '\n') : '';
         var clean2 = typeof wiki2 === 'string' ? 
            wiki2.replace(/(\r\n|\n|\r)/gm, '\n') : '';

        return clean1 !== clean2;
    };

    self.changed = function() {
        return self.wikisDiffer(self.initText(), self.currentText());
    };

    // Fetch initial wiki text
    self.fetchData = function() {
        var request = $.ajax({
            type: 'GET',
            url: url,
            dataType: 'json'
        });
        request.done(function (response) {
            // Most recent version, whether saved or in mongo
            self.initText(response.wiki_draft);
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

    // Revert to last saved version, even if draft is more recent
    self.revertChanges = function() {
        return self.fetchData().then(function(response) {
            // Dirty check now covers last saved version
            self.initText(response.wiki_content);
            self.currentText(response.wiki_content);
        });
    };

    $(window).on('beforeunload', function() {
        if (self.changed() && self.status() !== 'connected') {
            return 'There are unsaved changes to your wiki. If you exit ' +
                'the page now, those changes may be lost.';
        }
    });

}

function WikiEditor(url, viewText, editor) {
    this.viewModel = new ViewModel(url, viewText);
    var mdConverter = Markdown.getSanitizingConverter();
    var mdEditor = new Markdown.Editor(mdConverter);
    mdEditor.run(editor);

}

module.exports = WikiEditor;
