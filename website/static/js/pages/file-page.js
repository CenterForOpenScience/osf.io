var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var FileViewPage = require('js/filepage');
var waterbutler = require('js/waterbutler');

require('../../vendor/bower_components/jquery.tagsinput/jquery.tagsinput.css');
require('jquery-tagsinput');

m.mount(document.getElementsByClassName('file-view-panels')[0], FileViewPage(window.contextVars));


var guid = window.contextVars.file.file_guid;

    // Tag input
    $('#node-tags').tagsInput({
        width: '100%',
        interactive: window.contextVars.currentUser.canEdit,
        maxChars: 128,
        onAddTag: function(tag){
            var url = nodeApiUrl + 'file/tags/' + guid + '/';
            var request = $.ajax({
                url: url,
                type: 'POST',
                contentType: 'application/json',
                dataType: 'JSON',
                data: JSON.stringify({tag: tag, fileName: window.contextVars.file.name}),
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to add tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            });
        },
        onRemoveTag: function(tag){
            var url = nodeApiUrl + 'file/tags/' + guid + '/';
            var request = $.ajax({
                url: url,
                type: 'DELETE',
                contentType: 'application/json',
                dataType: 'JSON',
                data: JSON.stringify({tag: tag, fileName: window.contextVars.file.name}),
            });
            request.fail(function(xhr, textStatus, error) {
                Raven.captureMessage('Failed to remove tag', {
                    tag: tag, url: url, textStatus: textStatus, error: error
                });
            });
        }
    });

    // Limit the maximum length that you can type when adding a tag
    $('#node-tags_tag').attr('maxlength', '128');
