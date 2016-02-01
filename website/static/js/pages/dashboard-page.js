/**
 * Initialization code for the dashboard pages.
 */

'use strict';

var Raven = require('raven-js');
var $ = require('jquery');
var jstz = require('jstimezonedetect');

var $osf = require('js/osfHelpers');
var Dashboard = require('js/dashboard.js').Dashboard;
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.

var ensureUserTimezone = function(savedTimezone, savedLocale, id) {
    var clientTimezone = jstz.determine().name();
    var clientLocale = window.navigator.userLanguage || window.navigator.language;

    if (savedTimezone !== clientTimezone || savedLocale !== clientLocale) {
        var url = '/api/v1/profile/';

        var request = $osf.putJSON(
            url,
            {
                'timezone': clientTimezone,
                'locale': clientLocale,
                'id': id
            }
        );
        request.fail(function(xhr, textStatus, error) {
            Raven.captureMessage('Could not set user timezone or locale', {
                url: url,
                textStatus: textStatus,
                error: error
            });
        });
    }
};

$(document).ready(function() {
    m.mount(document.getElementById('dashboard'), m.component(Dashboard, {wrapperSelector : '#dashboard'}));
    // TODO: new data does not have timezone information
    //ensureUserTimezone(result.timezone, result.locale, result.id);

    setTimeout(function(){
        if($('#dashboard .spinner-loading-wrapper').length > 0) {
            $('#dashboard').append('<div class="text-danger text-center text-bigger">This is taking longer than normal. <br>  Try reloading the page. If the problem persist contact us at support@cos.io.</div>')
        }
    }, 10000);
    // Add active class to navigation for my projects page
    $('#osfNavMyProjects').addClass('active');
});

