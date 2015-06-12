/*
 * TODO, bring the register page up to date.
 *
 */
var $ = require('jquery');
var bootbox = require('bootbox');


var preRegisterMessage =  function(title, parentTitle, parentUrl, category) {
    // TODO(hrybacki): Remove warning once Retraction/Embargoes goes is merged into production
    if (parentUrl) {
        return 'You are about to register the ' + category + ' <b>' + title +
            '</b> including all components and data within it. This will <b>not</b> register' +
            ' its parent, <b>' + parentTitle + '</b>.' +
            ' If you want to register the parent, please go <a href="' +
            parentUrl + '">here.</a>' +
            // TODO(hrybacki): Remove once Retraction/Embargoes goes is merged into production
            '<hr /><b>Important Note:</b> As early as <u>June 8, 2015</u>, registrations ' +
            'will be made public immediately or can be embargoed for up to four years. ' +
            'There will no longer be the option of creating a permanently private ' +
            'registration. If you register before June 8, 2015 and leave your ' +
            'registration private, then the registration can remain private. After June 8, 2015, ' +
            'if you ever make it public, you will not be able to return it to private. ';
    } else {
        return 'You are about to register <b>' + title + '</b> ' +
            'including all components and data within it. ' +
            'Registration creates a permanent, time-stamped, uneditable version ' +
            'of the project. If you would prefer to register only one particular ' +
            'component, please navigate to that component and then initiate registration.' +
            // TODO(hrybacki): Remove once Retraction/Embargoes goes is merged into production
            '<hr /><b>Important Note:</b> As early as <u>June 8, 2015</u>, registrations ' +
            'will be made public immediately or can be embargoed for up to four years. ' +
            'There will no longer be the option of creating a permanently private ' +
            'registration. If you register before June 8, 2015 and leave your ' +
            'registration private, then the registration can remain private. After June 8, 2015, ' +
            'if you ever make it public, you will not be able to return it to private.';
    }
};

$(document).ready(function() {
    $('#registerNode').click(function(event) {
        var node = window.contextVars.node;
        var target = event.currentTarget.href;

        event.preventDefault();
        var title = node.title;
        var parentTitle = node.parentTitle;
        var parentRegisterUrl = node.parentRegisterUrl;
        var category = node.category;
        var bootboxTitle = 'Register ' + title;
        if (node.category !== 'project'){
            category = 'component';
        }

        bootbox.confirm({
            title: bootboxTitle,
            message: preRegisterMessage(title, parentTitle, parentRegisterUrl, category),
            callback: function (confirmed) {
                if(confirmed) {
                    window.location.href = target;
                }
            }
        });
    });
});
