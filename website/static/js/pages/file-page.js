var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var FileViewPage = require('js/filepage');
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
        defaultText: 'Add a tag to enhance discoverability',
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

    // allows inital default message to fit on empty tag
    if(!$('.tag').length){
        $('#fileTags_tag').css('width', '250px');
    }

    $('#fileTags_tag').attr('maxlength', '128');
    if (!window.contextVars.currentUser.canEdit || window.contextVars.node.isRegistration) {
        $('a[title="Removing tag"]').remove();
        $('span.tag span').each(function(idx, elm) {
            $(elm).text($(elm).text().replace(/\s*$/, ''));
        });
    }

    var titleEditable = function () {
        var readOnlyProviders = ['bitbucket', 'figshare', 'dataverse', 'gitlab', 'onedrive'];
        var ctx = window.contextVars;
        if (readOnlyProviders.indexOf(ctx.file.provider) >= 0 || ctx.file.checkoutUser || !ctx.currentUser.canEdit || ctx.node.isRegistration)
            return false;
        else
            return true;
    };

    if(titleEditable()) {
        $('#fileTitleEditable').editable({
            type: 'text',
            mode: 'inline',
            send: 'always',
            url: window.contextVars.file.urls.delete,
            ajaxOptions: {
                type: 'post',
                contentType: 'application/json',
                dataType: 'json',
                beforeSend: $osf.setXHRAuthorization,
                crossOrigin: true,
            },
            validate: function(value) {
                if($.trim(value) === ''){
                    return 'The file title cannot be empty.';
                } else if(value.length > 100){
                    return 'The file title cannot be more than 100 characters.';
                }
            },
            params: function(params) {
                var payload = {
                    action: 'rename',
                    rename: params.value,
                };
                return JSON.stringify(payload);
            },
            success: function(response) {
                $osf.growl('Success', 'Your file was successfully renamed. To view the new filename in the file tree below, refresh the page.', 'success');
            },
            error: function (response) {
                var msg = response.responseJSON.message;
                if (msg) {
                    // This is done to override inherited css style and prevent error message lines from overlapping with each other
                    $('.editable-error-block').css('line-height', '35px');
                    return msg;
                }
            }
        });
    }
});
