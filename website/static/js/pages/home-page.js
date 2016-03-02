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


$(document).ready(function(){
    var osfHome = {
        view : function(ctrl, args) {
            return [
                m('.quickSearch', m('.container.p-t-lg',
                    [
                        m('h3', [
                            m('span', 'My Projects'),
                            m('button.btn.btn-success.btn-xs', 'New Project')
                            ]
                        ),
                        m.component(quickSearchProject, {})
                    ]
                )),
                m('.recentActvity', m('.container',
                    [
                        m('h3', 'Recent Activity'),
                        m.component(LogWrap, {wrapper: 'recentActivity'})
                    ]
                )),
                m('.newAndNoteworthy', m('.container',
                    [
                        m('h3', 'Discover Public Projects'),
                        m.component(newAndNoteworthy, {})
                    ]
                )),
                m('.meetings', m('.container',
                    [
                        m.component(meetingsAndConferences, {})
                    ]
                ))
            ];
        }
    };
    // If logged in...
    m.mount(document.getElementById('osfHome'), m.component(osfHome, {}));



});
