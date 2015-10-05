var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var FileViewPage = require('js/filepage');
var waterbutler = require('js/waterbutler');

require('jquery-tagsinput');

m.mount(document.getElementsByClassName('file-view-panels')[0], FileViewPage(window.contextVars));

$(function() {
    // Tag input
    $('#fileTags').tagsInput({
        width: '100%',
        interactive: window.contextVars.currentUser.canEdit,
        maxChars: 128,
        onAddTag: function (tag) {
            var url = '/api/v1/project/' + window.contextVars.node.id + '/osfstorage' + window.contextVars.file.path +
                    '/tags/' + tag + '/';
            var request = $osf.postJSON(url);
            request.fail(function (xhr, textStatus, error) {
                Raven.captureMessage('Failed to add tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            });
        },
        onRemoveTag: function (tag) {
            var url = '/api/v1/project/' + window.contextVars.node.id + '/osfstorage' + window.contextVars.file.path +
                    '/tags/' + tag + '/';
            var request = $.ajax({
                url: url,
                type: 'DELETE',
                contentType: 'application/json',
                dataType: 'JSON',
            });
            request.fail(function (xhr, textStatus, error) {
                Raven.captureMessage('Failed to remove tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            });
        }
    });
});
