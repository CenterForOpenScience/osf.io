/**
 * Initialization code for the Wiki view page.
 */
'use strict';

var $ = require('jquery');
var Raven = require('raven-js');
var $osf = require('osfHelpers');
require('bootstrap-editable');

var mathrender = require('mathrender');

// Typeset math on the page
mathrender.mathjaxify('#wikiContent');

var ctx = window.contextVars;  // mako context variables

// Apply an empty ViewModel to the #wikiName element so that
// we can use the tooltip binding handler. =/
$osf.applyBindings({}, '#wikiName');


if (ctx.canEditPageName) {
    // Initialize editable wiki page name
    var $pageName = $('#pageName');
    $.fn.editable.defaults.mode = 'inline';
    $pageName.editable({
        type: 'text',
        send: 'always',
        url: ctx.urls.wikiRename,
        ajaxOptions: {
            type: 'put',
            contentType: 'application/json',
            dataType: 'json'
        },
        validate: function(value) {
            if($.trim(value) === ''){
                return 'The wiki page name cannot be empty.';
            } else if(value.length > 100){
                return 'The wiki page name cannot be more than 100 characters.';
            }
        },
        params: function(params) {
            return JSON.stringify(params);
        },
        success: function(response, value) {
            window.location.href = ctx.urls.wikiBase + encodeURIComponent(value) + '/';
        },
        error: function(response) {
            var msg = response.responseJSON.message_long;
            if (msg) {
                return msg;
            } else {
                // Log unexpected error with Raven
                Raven.captureMessage('Error in renaming wiki', {
                    url: ctx.urls.wikiRename,
                    responseText: response.responseText,
                    statusText: response.statusText
                });
                return 'An unexpected error occurred. Please try again.';
            }
        }
    });
}
