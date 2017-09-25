/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');
var lodashGet = require('lodash.get');

var QuickSearchProject = require('js/home-page/quickProjectSearchPlugin');
var NewAndNoteworthy = require('js/home-page/newAndNoteworthyPlugin');
var MeetingsAndConferences = require('js/home-page/meetingsAndConferencesPlugin');
var Preprints = require('js/home-page/preprintsPlugin');
var Prereg = require('js/home-page/preregPlugin');
var PreregBanner = require('js/home-page/preregBannerPlugin');
var InstitutionsPanel = require('js/home-page/institutionsPanelPlugin');
var ensureUserTimezone = require('js/ensureUserTimezone');

var columnSizeClass = '.col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2';

$(document).ready(function(){
    var osfHome = {
        view : function(ctrl, args) {
            // Camel-case institutions keys
            var _affiliatedInstitutions = lodashGet(window, 'contextVars.currentUser.institutions') || [];
            var affiliatedInstitutions = _affiliatedInstitutions.map(function(inst) {
                return {logoPath: inst.logo_path, id: inst.id, name: inst.name};
            });
            var _dashboardInstitutions = lodashGet(window, 'contextVars.dashboardInstitutions') || [];
            var dashboardInstitutions = _dashboardInstitutions.map(function(inst) {
                return {logoPath: inst.logo_path, id: inst.id, name: inst.name};
            });
            return [
                m('.quickSearch', m('.container.p-t-lg',
                    [
                        m('.row.m-t-lg', [
                            m(columnSizeClass, m.component(QuickSearchProject, {}))
                        ])
                    ]
                ))
            ];
        }
    };
    m.mount(document.getElementById('osfHome'), m.component(osfHome, {}));


    // If logged in...
    var user = window.contextVars.currentUser;
    if (user) {
        // Update user's timezone and locale
        ensureUserTimezone(user.timezone, user.locale, user.id);
    }
});
