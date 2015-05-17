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
            '</b> and everything that is inside it. This will <b>not</b> register' +
            ' its parent, <b>' + parentTitle + '</b>.' +
            ' If you want to register the parent, please go <a href="' +
            parentUrl + '">here.</a>' +
            '<hr /><b>Important Note:</b> Effective <u>29-May-2015</u>, public registrations ' +
            'will no longer be able to be made private. They will instead need to be retracted ' +
            'leaving behind basic meta-data related to the registration. If you would like ' +
            'your registration to be private, ensure that you take necessary action '+
            'before 29-May-2015.';
    } else {
        return 'You are about to register <b>' + title +
            '</b> and everything that is inside it. If you would prefer to register ' +
            'a particular component, please ' +
            'navigate to that component and then initiate registration.' +
            '<hr /><b>Important Note:</b> Effective <u>29-May-2015</u>, public registrations ' +
            'will no longer be able to be made private. They will instead need to be retracted ' +
            'leaving behind basic meta-data related to the registration. If you would like ' +
            'your registration to be private, ensure that you take necessary action '+
            'before 29-May-2015.';
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
        var bootboxTitle = 'Register Project';
        if (node.category !== 'project'){
            category = 'component';
            bootboxTitle = 'Register Component';
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
