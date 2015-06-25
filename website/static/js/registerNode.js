/*
 * TODO, bring the register page up to date.
 *
 */
var $ = require('jquery');
var bootbox = require('bootbox');
var $osf = require('js/osfHelpers');
var ctx = window.contextVars;

var preRegisterMessage =  function(title, parentTitle, parentUrl, category) {
    // TODO(hrybacki): Remove warning once Retraction/Embargoes goes is merged into production
    if (parentUrl) {
        return 'You are about to register the ' + category + ' <b>' + title +
            '</b> including all components and data within it. This will <b>not</b> register' +
            ' its parent, <b>' + parentTitle + '</b>.' +
            ' If you want to register the parent, please go <a href="' +
            parentUrl + '">here.</a> After selecting OK, you will next select a registration form.';
    } else {
        return 'You are about to register <b>' + title + '</b> ' +
            'including all components and data within it. ' +
            'Registration creates a permanent, time-stamped, uneditable version ' +
            'of the project. If you would prefer to register only one particular ' +
            'component, please navigate to that component and then initiate registration. ' +
            'After selecting OK, you will next select a registration form.';
    }
};

function draft_failed() {
    $osf.unblock();
    bootbox.alert('Draft failed');
}

function draftNode() {

    // Block UI until request completes
    $osf.block();

    // POST data
    $.ajax({
        url:  ctx.node.urls.api + 'draft/' + ctx.regTemplate + '/',
        type: 'POST',
        //contentType: 'application/json',
    }).done(function(response) {
        if (response.status === 'success') {
            window.location.href = response.result;
        }
        else if (response.status === 'error') {
            draft_failed();
        }
    }).fail(function() {
        draft_failed();
    });

    // Stop event propagation
    return false;

}

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
                    $('#registerNodeForm').submit();
                }
            }
        });
    });
});
