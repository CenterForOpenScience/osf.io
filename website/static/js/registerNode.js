/*
 * TODO, bring the register page up to date. 
 *
 */
var $ = require('jquery');
var bootbox = require('bootbox');

var preRegisterMessage =  function(title, parentTitle, parentUrl) {
    return 'You are about to Register the component "' + title +
        '" and everything that is inside it. This will not register' +
        ' your larger project "' + parentTitle + '" and its other components.' +
        ' If you want to register the entire project, please go <a href="' +
        parentUrl + '">here.</a>';
};

$(document).ready(function() {
    $('#registerNode').click(function(event) {
        var node = window.contextVars.node;
        var target = event.currentTarget.href;
        if (node.parentExists) {
            event.preventDefault();
            var title = node.title;
            var parentTitle = node.parentTitle;
            var parentRegisterUrl = node.parentRegisterUrl;
            
            bootbox.confirm(preRegisterMessage(title, parentTitle, parentRegisterUrl), function(result) {
                if (result) {
                    window.location.href = target;
                }
            });
        }        
    });
});
