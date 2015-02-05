var $ = require('jquery');
var bootbox = require('bootbox');

var ProjectSettings = require('../projectSettings.js');

var $osf = require('osfHelpers');

var ctx = window.contextVars;

// Initialize treebeard grid
var ProjectNotifications = require('../project-settings-treebeard.js');
var data = [];
new ProjectNotifications(window.contextVars.node.subscriptions);


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
            nodeApiUrl + 'settings/comments/',
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

    // Submit for notifications preferences
    var $notificationSettings = $('#notificationSettings');

    $notificationSettings.on('submit', function() {
        var $notificationsMsg = $('#configureNotificationsMessage');

        var payload = {};

        $notificationSettings.find('.form-control').each(function(idx, elm) {
            var pid = $(elm).attr('id'); //uw8fk
            var event = $(elm).attr('name'); //comments

            if (payload[pid] === undefined) {
                payload[pid] = {};
            }
            payload[pid][event] = {};

            $(elm).find('option').each(function(idx, elm) {
                var notificationType = $(elm).attr('value');

                if (notificationType !== "adopt_parent") {
                    payload[pid][event][notificationType] = $(elm).is(':selected');
                }
            });
        });

        $osf.postJSON(
            '/api/v1/settings/batch_subscribe/',
            payload
        ).done(function() {
            $notificationsMsg.addClass('text-success');
            $notificationsMsg.text('Successfully updated notification preferences');
            window.location.reload();
        }).fail(function() {
            bootbox.alert('Could not update notification preferences.')
        });
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


