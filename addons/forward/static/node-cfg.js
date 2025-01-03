var $osf = require('js/osfHelpers');
var ForwardConfig = require('./forwardConfig.js');

var ctx = window.contextVars;

var enabled = false;
var url = '';
var label = '';

$(document).ready(function() {
    $osf.ajaxJSON(
        'GET',
        $osf.apiV2Url('nodes/' + ctx.node.id + '/addons/forward'),
        {'isCors': true}
    ).done(function(response){
        enabled = true;
        url = response.data.attributes.url;
        label = response.data.attributes.label;
        new ForwardConfig('#configureForward', ctx.node, enabled, url, label);
    }).fail(function(response){
        if (response.status === 404) {
            new ForwardConfig('#configureForward', ctx.node, enabled, url, label);
            return;
        }
        $osf.growl('Error:', 'Unable to retrieve settings.');
        Raven.captureMessage('Error occurred retrieving node addons');
    });

});


