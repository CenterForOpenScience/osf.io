var $ = require('jquery');

// initialize view model for configuring mailchimp subscriptions
var NotificationsConfig =  require('../notificationsConfig.js');
new NotificationsConfig('#selectLists', window.contextVars.mailingList);

//initialize treebeard for notification subscriptions
var ProjectNotifications = require('../project-settings-treebeard.js');
var $notificationsMsg = $('#configureNotificationsMessage');

$.ajax({
        url: '/api/v1/subscriptions',
        type: 'GET',
        dataType: 'json',
        success: function(response) {
            new ProjectNotifications(response);
        },
        error: function() {
            $notificationsMsg.addClass('text-danger');
            $notificationsMsg.text('Could not retrieve notification settings.');
        }
});
