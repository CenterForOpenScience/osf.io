/*
 * TODO, bring the register page up to date.
 *
 */
var $ = require('jquery');
var bootbox = require('bootbox');


var preRegisterMessage =  function(title, parentTitle, parentUrl, category) {
    if (parentUrl) {
        return 'You are about to register the ' + category + ' <b>' + title +
            '</b> and everything that is inside it. This will <b>not</b> register' +
            ' its parent, <b>' + parentTitle + '</b>.' +
            ' If you want to register the parent, please go <a href="' +
            parentUrl + '">here.</a>';
    } else {
        return 'You are about to register <b>' + title +
            '</b> and everything that is inside it. If you would prefer to register ' +
            'a particular component, please ' +
            'navigate to that component and then initiate registration.';
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
