/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');

var QuickSearchProject = require('js/home-page/quickProjectSearchPlugin');
var NewAndNoteworthy = require('js/home-page/newAndNoteworthyPlugin');
var MeetingsAndConferences = require('js/home-page/meetingsAndConferencesPlugin');
var UsersInstitutions = require('js/home-page/usersInstitutionsPlugin');

var columnSizeClass = '.col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2';

$(document).ready(function(){
    var osfHome = {
        view : function(ctrl, args) {
            var userInstitutions = window.contextVars.user_institutions;
            return [
                m('.quickSearch', m('.container.p-t-lg',
                    [
                        m('.row.m-t-lg', [
                            m(columnSizeClass, m.component(QuickSearchProject, {}))
                        ])
                    ]
                )),
                m('', userInstitutions ? m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass, m('h3', 'User Institutions'))
                        ]),
                        m('.row', [
                            m(columnSizeClass, m.component(UsersInstitutions, {institutions: userInstitutions}))
                        ])
                    ]
                ) : ''),
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
