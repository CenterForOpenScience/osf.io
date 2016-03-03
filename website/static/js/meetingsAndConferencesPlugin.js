/**
 * Meetings and Conferences
 */

var m = require('mithril');

// CSS
require('css/quick-project-search-plugin.css');

var MeetingsAndConferences = {
    view: function(ctrl) {
        return m('.conferences-and-meetings.p-v-sm',
            m('.row',
                [
                    m('.col-md-8',
                        [
                            m('div.conference-centering',  m('h2', 'Hosting a Conference or Meeting?')),
                            m('div.conference-centering',
                                m('p.text-bigger', 'Use the OSF meetings service to provide a central location for collection submissions!')
                            )
                        ]
                    ),
                    m('.col-md-4.text-center',
                        m('div',  m('a.btn.btn-info.btn-lg.m-v-xl', {type:'button',  href:'/meetings/'}, 'Create a Meeting'))
                    )
                ]
            )
        );
    }
};


module.exports = MeetingsAndConferences;
