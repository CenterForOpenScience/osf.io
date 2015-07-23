'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var AddonHelper = require('js/addonHelper');
var language = require('js/osfLanguage').Addons.s3;

$('#s3RemoveAccess').on('click', function() {
    bootbox.confirm({
        title: 'Disconnect S3 Account?',
        message: language.confirmDeauth,
        callback: function(result) {
            if(result) {
                deleteToken();
            }
        },
        buttons:{
            confirm:{
                label:'Disconnect',
                className:'btn-danger'
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
