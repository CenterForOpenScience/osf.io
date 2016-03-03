/**
 * Initialization code for the home page.
 */

'use strict';

var $ = require('jquery');
var m = require('mithril');

var quickSearchProject = require('js/quickProjectSearchPlugin');
var newAndNoteworthy = require('js/newAndNoteworthyPlugin');
var meetingsAndConferences = require('js/meetingsAndConferencesPlugin');
var LogWrap = require('js/recentActivityWidget');

var columnSizeClass = '.col-md-10 col-md-offset-1 col-lg-8 col-lg-offset-2';

$(document).ready(function(){
    var osfHome = {
        view : function(ctrl, args) {
            return [
                m('.quickSearch', m('.container.p-t-lg',
                    [
                        m('.row', [
                            m('.col-xs-6 col-md-5 col-md-offset-1 col-lg-4 col-lg-offset-2', m('h3', 'My Projects')),
                            m('.col-xs-6 col-md-5 col-md-offset-1 col-lg-4 col-lg-offset-2', m('button.btn.btn-success.btn-xs', 'New Project'))
                        ]),
                        m('.row', [
                            m(columnSizeClass, m.component(quickSearchProject, {}))
                        ])
                    ]
                )),
                m('.recentActvity', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,m('h3', 'Recent Activity'))
                        ]),
                        m('.row', [
                            m(columnSizeClass, m.component(LogWrap, {wrapper: 'recentActivity'}))
                        ])

                    ]
                )),
                m('.newAndNoteworthy', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,m('h3', 'Discover Public Projects'))
                        ]),
                        m('.row', [
                            m(columnSizeClass, m.component(newAndNoteworthy, {}))
                        ])

                    ]
                )),
                m('.meetings', m('.container',
                    [
                        m('.row', [
                            m(columnSizeClass,  m.component(meetingsAndConferences, {}))
                        ])

                    ]
                ))
            ];
        }
    };
    // If logged in...
    m.mount(document.getElementById('osfHome'), m.component(osfHome, {}));



});
