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

var _ = require('js/rdmGettext')._;
var sprintf = require('agh.sprintf').sprintf;

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
            Raven.captureMessage(_('Could not set user timezone or locale'), {
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    }
};

$(document).ready(function() {
    m.mount(document.getElementById('dashboard'), m.component(MyProjects, {wrapperSelector : '#dashboard'}));

    var OSF_SUPPORT_EMAIL = window.contextVars.osfSupportEmail;
    // Appears in 10 second if the spinner is still there.
    setTimeout(function(){
        if($('#dashboard>.ball-scale').length > 0) {
            $('#dashboard').append('<div class="text-danger text-center text-bigger">' + sprintf(_('This is taking longer than normal. <br>  Try reloading the page. If the problem persist, please contact us at %1$s') , OSF_SUPPORT_EMAIL) + '.</div>');
        }
    }, 10000);
});
