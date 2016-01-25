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


var meetingsAndConferences = {
    controller: function() {
        var self = this;
        self.findAMeeting = function(){
            location.href = '/meetings/';
        };
    },
    view: function(ctrl) {
        function findAMeetingButton() {
             return m('button', {type:'button', 'class':'btn btn-default btn-block m-v-xl', onclick: function(){
                ctrl.findAMeeting();
            }}, 'Find a Meeting');

        }

        function createAMeetingButton() {
             return m('button', {type:'button', 'class':'btn btn-default btn-block m-v-xl', onclick: function(){
                ctrl.findAMeeting();
            }}, 'Create a Meeting');
        }
        return m('div', {'class': 'container conferences-and-meetings m-v-md'}, [
            m('div', {'class': 'row m-v-sm'},
                m('div', {'class': 'col-sm-5'},
                    m('div', {'class': 'row'},
                        m('div', {'class': 'col-sm-offset-1 col-xs-offset-1'},
                            m('div', {'class': 'col-sm-11'}, m('h3', 'Hosting a Conference or Meeting?')),
                            m('div', {'class': 'col-sm-1'})
                        )
                    ),
                    m('div', {'class': 'row'},
                        m('div', {'class': 'col-sm-offset-1 col-xs-offset-1'},
                            m('div', {'class': 'col-sm-11'},  m('h6', 'Use the OSF meetings service to provide a central location for collection submissions!'), m('a', {href: '/meetings/'}, 'Learn more')),
                            m('div', {'class': 'col-sm-1'})
                        )
                    )
                ),
                m('div', {'class': 'col-sm-7'},
                    m('div', {'class': 'row'}),
                    m('div', {'class': 'row'},
                        m('div', {'class': 'col-sm-1'}),
                        m('div', {'class': 'col-sm-5'}, findAMeetingButton()),
                        m('div', {'class': 'col-sm-5'}, createAMeetingButton()),
                        m('div', {'class': 'col-sm-1'})
                    ))
            )
        ]);
    }
};


module.exports = meetingsAndConferences;