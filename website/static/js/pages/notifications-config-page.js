// initialize view model for configuring mailchimp subscriptions
var NotificationsConfig =  require('../notificationsConfig.js');
new NotificationsConfig('#selectLists', window.contextVars.mailingList);

//initialize treebeard for notification subscriptions
var ProjectNotifications = require('../project-settings-treebeard.js');
new ProjectNotifications(window.contextVars.notificationsData);
