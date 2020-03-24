var $ = require('jquery');

// initialize view model for configuring mailchimp subscriptions
var NotificationsConfig =  require('../notificationsConfig.js');
new NotificationsConfig('#selectLists', window.contextVars.mailingLists);

//initialize treebeard for notification subscriptions
var ProjectNotifications = require('../notificationsTreebeard.js');
var $notificationsMsg = $('#configureNotificationsMessage');

var rdmGettext = require('js/rdmGettext');
var gt = rdmGettext.rdmGettext();
var _ = function(msgid) { return gt.gettext(msgid); };

$.ajax({
    url: '/api/v1/subscriptions',
    type: 'GET',
    dataType: 'json'
}).done( function(response) {
    new ProjectNotifications(response);
}).fail( function() {
    $notificationsMsg.addClass('text-danger');
    $notificationsMsg.text(_('Could not retrieve notification settings.'));
});
