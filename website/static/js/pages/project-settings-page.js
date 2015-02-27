'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');

var ProjectSettings = require('../projectSettings.js');

var $osf = require('osfHelpers');
require('../../css/addonsettings.css');

var ctx = window.contextVars;

$(document).ready(function() {

    $('#deleteNode').on('click', function() {
        ProjectSettings.getConfirmationCode(ctx.node.nodeType);
    });

    // TODO: Knockout-ify me
    $('#commentSettings').on('submit', function() {
        var $commentMsg = $('#configureCommentingMessage');

        var $this = $(this);
        var commentLevel = $this.find('input[name="commentLevel"]:checked').val();

        $osf.postJSON(
            ctx.node.urls.api + 'settings/comments/',
            {commentLevel: commentLevel}
        ).done(function() {
            $commentMsg.addClass('text-success');
            $commentMsg.text('Successfully updated settings.');
            window.location.reload();
        }).fail(function() {
            bootbox.alert('Could not set commenting configuration. Please try again.');
        });

        return false;

    });


    // Set up submission for addon selection form
    $('#selectAddonsForm').on('submit', function() {

        var formData = {};
        $('#selectAddonsForm').find('input').each(function(idx, elm) {
            var $elm = $(elm);
            formData[$elm.attr('name')] = $elm.is(':checked');
        });
        var msgElm = $(this).find('.addon-settings-message');
        $.ajax({
            url: ctx.node.urls.api + 'settings/addons/',
            data: JSON.stringify(formData),
            type: 'POST',
            contentType: 'application/json',
            dataType: 'json',
            success: function() {
                msgElm.text('Settings updated').fadeIn();
                window.location.reload();
            }
        });

        return false;

    });



    // Show capabilities modal on selecting an addon; unselect if user
    // rejects terms
    $('.addon-select').on('change', function() {
        var that = this,
            $that = $(that);
        if ($that.is(':checked')) {
            var name = $that.attr('name');
            var capabilities = $('#capabilities-' + name).html();
            if (capabilities) {
                bootbox.confirm(
                    capabilities,
                    function(result) {
                        if (!result) {
                            $(that).attr('checked', false);
                        }
                    }
                );
            }
        }
    });

});
