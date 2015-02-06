var $ = require('jquery');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');

//initialize treebeard
var ProjectNotifications = require('./project-settings-treebeard.js');
new ProjectNotifications(window.contextVars.notificationsData);


$(document).ready(function() {

    var $notifications = $('#selectNotifications');

    $notifications.on('submit', function() {
        var $notificationsMsg = $('#configureNotificationsMessage');

        var payload = {};

        $notifications.find('.form-group').each(function(idx, elm) {
            var pid = $(elm).attr('id');
            var event = $(elm).find('.form-control').attr('name');

            if (payload[pid] === undefined) {
                payload[pid] = {};
            }
            payload[pid][event] = {};

            $(elm).find('.form-control').find('option').each(function(idx, elm) {
                var notificationType = $(elm).attr('value');
                payload[pid][event][notificationType] = $(elm).is(':selected');
            });

        });

        $osf.postJSON(
            '/api/v1/settings/batch_subscribe/',
            payload
        ).done(function() {
            $notificationsMsg.addClass('text-success');
            $notificationsMsg.text('Settings updated.');
            window.location.reload();
        }).fail(function() {
            bootbox.alert('Could not update notification preferences.')
        });

    });

});