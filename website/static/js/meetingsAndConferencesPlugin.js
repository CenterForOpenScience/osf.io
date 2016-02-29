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
                    m('.col-md-6',
                        [
                            m('div.conference-centering',  m('h2', 'Hosting a Conference or Meeting?')),
                            m('div.conference-centering',
                                m('p.text-bigger', 'Use the OSF meetings service to provide a central location for collection submissions!')
                            )
                        ]
                    ),
                    m('.col-md-6',
                        m('.row', [
                            m('div', {'class': 'col-xs-6'}, m('a.btn.btn-block.m-v-xl', {type:'button', href:'/meetings/'}, 'Find a Meeting')),
                            m('div', {'class': 'col-xs-6'}, m('a.btn.btn-block.m-v-xl', {type:'button',  href:'/meetings/'}, 'Create a Meeting'))
                        ])
                    )
                ]
            )
        );
    }
};


module.exports = MeetingsAndConferences;
