/**
 * Meetings and Conferences
 */

var m = require('mithril');
var $osf = require('js/osfHelpers');

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
                                m('p.text-bigger', 'Use the GakuNin RDM for Meetings service to provide a central location for conference submissions.')
                            )
                        ]
                    ),
                    m('.col-md-4.text-center',
                        m('div',  m('a.btn.btn-banner.btn-success.btn-lg.btn-success-high-contrast.m-v-xl.f-w-xl', { type:'button',  href:'/meetings/', onclick: function() {
                            $osf.trackClick('meetingsAndConferences', 'navigate', 'navigate-to-view-meetings');
                        }}, 'View meetings'))
                    )
                ]
            )
        );
    }
};


module.exports = MeetingsAndConferences;
