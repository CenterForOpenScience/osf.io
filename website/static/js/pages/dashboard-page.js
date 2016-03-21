/**
 * Initialization code for the dashboard pages.
 */

'use strict';

var Raven = require('raven-js');
var $ = require('jquery');
var jstz = require('jstimezonedetect');

var $osf = require('js/osfHelpers');
var MyProjects = require('js/myProjects.js').MyProjects;
var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
require('loaders.css/loaders.min.css');

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
    m.mount(document.getElementById('dashboard'), m.component(MyProjects, {wrapperSelector : '#dashboard'}));
    // TODO: new data does not have timezone information
    //ensureUserTimezone(result.timezone, result.locale, result.id);

    // Appears in 10 second if the spinner is still there.
    setTimeout(function(){
        if($('#dashboard .ball-scale').length > 0) {
            $('#dashboard').append('<div class="text-danger text-center text-bigger">This is taking longer than normal. <br>  Try reloading the page. If the problem persist contact us at support@cos.io.</div>');
        }
    }, 10000);

    // Add active class to navigation for my projects page
    $('#osfNavMyProjects').addClass('active');
});

