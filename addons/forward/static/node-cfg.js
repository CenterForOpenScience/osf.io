var $osf = require('js/osfHelpers');
var ForwardConfig = require('./forwardConfig.js');

var ctx = window.contextVars;

var enabled = false;
var url = '';
var label = '';

$(document).ready(function() {
    $osf.ajaxJSON(
        'GET',
        $osf.apiV2Url('nodes/' + ctx.node.id + '/addons/'),
        {'isCors': true}
    ).done(function(response){
        response.data.forEach(function(addon) {
            if (addon.id === 'forward') {
                enabled = true;
                url = addon.attributes.url;
                label = addon.attributes.label;
            }
        });
        new ForwardConfig('#configureForward', ctx.node, enabled, url, label);
    }).fail(function(response){
        $osf.growl('Error:', 'Unable to retrieve settings.');
        Raven.captureMessage('Error occurred retrieving node addons');
    });

});


