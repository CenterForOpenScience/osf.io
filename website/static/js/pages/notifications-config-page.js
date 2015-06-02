var $ = require('jquery');

// initialize view model for configuring mailchimp subscriptions
var NotificationsConfig =  require('../notificationsConfig.js');
new NotificationsConfig('#selectLists', window.contextVars.mailingList);

//initialize treebeard for notification subscriptions
var ProjectNotifications = require('../notificationsTreebeard.js');
var $notificationsMsg = $('#configureNotificationsMessage');

$.ajax({
    url: '/api/v1/subscriptions',
    type: 'GET',
    dataType: 'json'
}).done( function(response) {
    new ProjectNotifications(response);
}).fail( function() {
    $notificationsMsg.addClass('text-danger');
    $notificationsMsg.text('Could not retrieve notification settings.');
});

//Fixes profile settings side menu to left column
function fixAffixWidth() {
    $('.affix, .affix-top, .affix-bottom').each(function (){
        var el = $(this);
        var colsize = el.parent('.affix-parent').width();
        el.outerWidth(colsize);
    });
}


$(document).ready(function() {
    $(window).resize(function (){ fixAffixWidth(); });
    $('.profile-page .panel').on('affixed.bs.affix', function(){ fixAffixWidth();});
});
