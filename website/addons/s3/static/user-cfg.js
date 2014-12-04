var AddonHelper = require('addon-helpers');
var $ = require('jquery');
var bootbox = require('bootbox');

$('#s3RemoveAccess').on('click', function() {
    bootbox.confirm({
        title: 'Remove access key?',
        message: 'Are you sure you want to remove your Amazon Simple Storage Service access key? ' +
                'This will revoke access to Amazon S3 for all projects you have authorized and ' +
                'delete your access token from Amazon S3. Your OSF collaborators will not be able ' +
                'to write to Amazon S3 buckets or view private buckets that you have authorized.',
        callback: function(result) {
            if(result) {
                deleteToken();
            }
        }
    });
});

function deleteToken() {
    var $this = $(this),
    addon = $this.attr('data-addon'),
    msgElm = $this.find('.addon-settings-message');
    $.ajax({
        type: 'DELETE',
        url: '/api/v1/settings/s3/',
        contentType: 'application/json',
        dataType: 'json',
        success: function(response) {
            msgElm.text('Keys removed')
                .removeClass('text-danger').addClass('text-success')
                .fadeOut(100).fadeIn();
            window.location.reload();
        },
        error: function(xhr) {
            var response = JSON.parse(xhr.responseText);
            if (response && response.message) {
                if(response.message === 'reload')
                    window.location.reload();
                else
                    message = response.message;
            } else {
                message = 'Error: Keys not removed';
            }
            msgElm.text(message)
                .removeClass('text-success').addClass('text-danger')
                .fadeOut(100).fadeIn();
        }
    });
    return false;
}

$(document).ready(function() {
    $(window.contextVars.addonSettingsSelector).on('submit', AddonHelper.onSubmitSettings);
});
