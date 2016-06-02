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
var InstitutionsPanel = require('js/home-page/institutionsPanelPlugin');

var columnSizeClass = '.col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2';

$(document).ready(function(){
    var osfHome = {
        view : function(ctrl, args) {
            // Camel-case institutions keys
            var _affiliatedInstitutions = lodashGet(window, 'contextVars.currentUser.institutions') || [];
            var affiliatedInstitutions = _affiliatedInstitutions.map(function(inst) {
                return {logoPath: inst.logo_path, id: inst.id, name: inst.name};
            });
            var _allInstitutions = lodashGet(window, 'contextVars.allInstitutions') || [];
            var allInstitutions = _allInstitutions.map(function(inst) {
                return {logoPath: inst.logo_path, id: inst.id, name: inst.name};
            });
            return [
                m('.quickSearch', m('.container.p-t-lg',
                    [
                        m('.row.m-t-lg', [
                            m(columnSizeClass, m.component(QuickSearchProject, {}))
                        ])
                    ]
                )),
                // TODO: We hide the institution logos on small screens. Better to make the carousel responsive.
                affiliatedInstitutions.length ? m('.institutions-panel.hidden-xs', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,  m.component(InstitutionsPanel, {
                                affiliatedInstitutions: affiliatedInstitutions,
                                allInstitutions: allInstitutions
                            }))
                        ])
                    ]
                )) : '',
                m('.newAndNoteworthy', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass, m('h3', 'Discover Public Projects'))
                        ]),
                        m('.row', [
                            m(columnSizeClass, m.component(NewAndNoteworthy, {}))
                        ])

                    ]
                )),
                m('.meetings', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,  m.component(MeetingsAndConferences, {}))
                        ])

                    ]
                ))
            ];
        }
    };
    // If logged in...
    m.mount(document.getElementById('osfHome'), m.component(osfHome, {}));
    $('#osfNavDashboard').addClass('active');



});
