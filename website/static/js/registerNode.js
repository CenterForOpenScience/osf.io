/*
 * TODO, bring the register page up to date.
 *
 */
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');

var registrationUtils = require('js/registrationUtils');

var ctx = window.contextVars;
var node = ctx.node;

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

        registrationUtils.

        bootbox.confirm({
            title: bootboxTitle,
            message: preRegisterMessage(title, parentTitle, parentRegisterUrl, category),
            callback: function (confirmed) {
                if(confirmed) {                    
                    //TODO
                }
            }
        });
    });
});
