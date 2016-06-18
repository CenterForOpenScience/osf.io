var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var FileViewPage = require('js/filepage');
var waterbutler = require('js/waterbutler');
var Raven = require('raven-js');

require('jquery-tagsinput');

m.mount(document.getElementsByClassName('file-view-panels')[0], FileViewPage(window.contextVars));

var tagUrl = '/api/v1/project/' + window.contextVars.node.id + '/osfstorage' + window.contextVars.file.path + '/tags/';

$(function() {
    // Tag input
    $('#fileTags').tagsInput({
        width: '100%',
        interactive: window.contextVars.currentUser.canEdit,
        maxChars: 128,
        onAddTag: function (tag) {
            var url = tagUrl;
            var request = $osf.postJSON(url, {'tag': tag });
            request.fail(function (xhr, textStatus, error) {
                $osf.growl('Error', 'Could not add tag.');
                Raven.captureMessage('Failed to add tag', {
                    extra: { tag: tag, url: url, textStatus: textStatus, error: error }
                });
            });
        },
        onRemoveTag: function (tag) {
            // Don't try to delete a blank tag (would result in a server error)
            if (!tag) {
                return false;
            }
            var request = $osf.ajaxJSON('DELETE', tagUrl, {'data': {'tag': tag}});
            request.fail(function (xhr, textStatus, error) {
                // Suppress "tag not found" errors, as the end result is what the user wanted (tag is gone)- eg could be because two people were working at same time
                if (xhr.status !== 409) {
                    $osf.growl('Error', 'Could not remove tag.');
                    Raven.captureMessage('Failed to remove tag', {
                        extra: {tag: tag, url: tagUrl, textStatus: textStatus, error: error}
                    });
                }
            });
        }
    });
    $('#fileTags_tag').attr('maxlength', '128');
    if (!window.contextVars.currentUser.canEdit || window.contextVars.node.isRegistration) {
        $('a[title="Removing tag"]').remove();
        $('span.tag span').each(function(idx, elm) {
            $(elm).text($(elm).text().replace(/\s*$/, ''));
        });
    }

});
