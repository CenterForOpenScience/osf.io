var $ = require('jquery');

// initialize view model for configuring mailchimp subscriptions
var NotificationsConfig =  require('../notificationsConfig.js');
new NotificationsConfig('#selectLists', window.contextVars.mailingList);

//initialize treebeard for notification subscriptions
var ProjectNotifications = require('../project-settings-treebeard.js');

$.ajax({
        url: '/api/v1/subscriptions',
        type: 'GET',
        dataType: 'json',
        success: function(response) {
            new ProjectNotifications(response);
        },
        error: function() {
            var message = 'Could not retrieve settings information.';
            self.changeMessage(message, 'text-danger', 5000);
        }
});
