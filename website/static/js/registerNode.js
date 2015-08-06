/*
 * TODO, bring the register page up to date.
 *
 */
var $ = require('jquery');
var bootbox = require('bootbox');

var $osf = require('js/osfHelpers');

var preRegisterMessage =  function(title, parentTitle, parentUrl, category) {
    var titleText = $osf.htmlEscape(title);
    var parentTitleText = $osf.htmlEscape(parentTitle);
    if (parentUrl) {
        return 'You are about to register the ' + category + ' <b>' + titleText +
            '</b> including all components and data within it. This will <b>not</b> register' +
            ' its parent, <b>' + parentTitleText + '</b>.' +
            ' If you want to register the parent, please go <a href="' +
            parentUrl + '">here.</a> After clicking Register, you will next select a registration form.';
    } else {
        return 'You are about to register <b>' + titleText + '</b> ' +
            'including all components and data within it. ' +
            'Registration creates a permanent, time-stamped, uneditable version ' +
            'of the project. If you would prefer to register only one particular ' +
            'component, please navigate to that component and then initiate registration. ' +
            'After clicking Register, you will next select a registration form.';
    }
};

$(document).ready(function() {
    $('#registerNode').click(function(event) {
        var node = window.contextVars.node;
        var target = event.currentTarget.href;

        event.preventDefault();
        var title = node.title;
        var titleText = $osf.htmlEscape(title);
        var parentTitle = node.parentTitle;
        var parentRegisterUrl = node.parentRegisterUrl;
        var category = node.category;
        var bootboxTitle = 'Register ' + titleText;
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
            },
            buttons:{
                confirm:{
                    label:'Register'
                }
            }
        });
    });
});
