/*
 * TODO, bring the register page up to date. 
 *
 */
var $ = require('jquery');
var bootbox = require('bootbox');


var preRegisterMessage =  function(title, parentTitle, parentUrl, category) {
    if (parentUrl) {
        return 'You are about to register the ' + category + ' <b>' + title +
            '</b> and everything that is inside it. This will not register' +
            ' your larger project "' + parentTitle + '" and its other components.' +
            ' If you want to register the parent project, please go <a href="' +
            parentUrl + '">here.</a>';
    } else {
        return 'You are about to register the project <b>' + title +
            '</b> and everything that is inside it. If you would prefer to register ' +
            'just a particular component of "' + title + '", please click back ' +
            'and navigate to that component and then initiate registration.';
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
