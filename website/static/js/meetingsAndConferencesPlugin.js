/**
 * Meetings and Conferences
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/quick-project-search-plugin.css');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var MeetingsAndConferences = {
    view: function(ctrl) {
        function findAMeetingButton() {
             return m('a.btn.btn-default.btn-block.m-v-xl', {type:'button', href:'/meetings/'}, 'Find a Meeting');
        }

        function createAMeetingButton() {
             return m('a.btn.btn-default.btn-block.m-v-xl', {type:'button',  href:'/meetings/'}, 'Create a Meeting');
        }
        return m('div.container.conferences-and-meetings.p-v-sm',
            m('div', {'class': 'col-sm-6 col-md-5'},
                m('div', {'class': 'row'},
                    m('div', {'class': 'col-md-offset-1'},
                        m('div.conference-centering', {'class': 'col-sm-11 col-xs-12'}, m('h3', 'Hosting a Conference or Meeting?')),
                        m('div', {'class': 'col-sm-1'})
                    )
                ),
                m('div', {'class': 'row'},
                    m('div', {'class': 'col-md-offset-1'},
                        m('div.conference-centering', {'class': 'col-sm-11 col-xs-12'},  m('h6', 'Use the OSF meetings service to provide a central location for collection submissions!'), m('span', m('a', {href: '/meetings/'}, 'Learn more'))),
                        m('div', {'class': 'col-sm-1'})
                    )
                )
            ),
            m('div', {'class': 'col-sm-6 col-md-7'},
                m('div', {'class': 'row'},
                    m('div',
                        m('div', {'class': 'col-xs-6'}, findAMeetingButton()),
                        m('div', {'class': 'col-xs-6'}, createAMeetingButton())
                ))
            )
        );
    }
};


module.exports = MeetingsAndConferences;
