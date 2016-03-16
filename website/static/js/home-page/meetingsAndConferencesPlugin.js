/**
 * Meetings and Conferences
 */

var m = require('mithril');

// CSS
require('css/meetings-and-conferences.css');

var MeetingsAndConferences = {
    view: function(ctrl) {
        return m('.p-v-sm',
            m('.row',
                [
                    m('.col-md-8',
                        [
                            m('div.conference-centering',  m('h3', 'Hosting a conference or meeting?')),
                            m('div.conference-centering.m-t-lg',
                                m('p.text-bigger', 'Use the OSF for Meetings service to provide a central location for conference submissions.')
                            )
                        ]
                    ),
                    m('.col-md-4.text-center',
                        m('div',  m('a.btn.btn-info.btn-lg.m-v-xl', { style : 'box-shadow: 0 0 9px -4px #000;', type:'button',  href:'/meetings/'}, 'View meetings'))
                    )
                ]
            )
        );
    }
};


module.exports = MeetingsAndConferences;
