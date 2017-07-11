/**
 * Preprints
 */

var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/meetings-and-conferences.css');


var Preprints = {
    view: function(ctrl) {
        return m('.p-v-sm',
            m('.row',
                [
                    m('.col-md-8',
                        [
                            m('div.conference-centering',  m('h3', 'Browse the latest research')),
                            m('div.conference-centering.m-t-lg',
                                m('p.text-bigger', 'Check out the latest Preprints hosted on the OSF covering a variety of research areas.')
                            )
                        ]
                    ),
                    m('.col-md-4.text-center',
                        m('div',  m('a.btn.btn-banner.btn-success.btn-lg.btn-success-high-contrast.m-v-xl.f-w-xl', { type:'button',  href:'/preprints/', onclick: function() {
                            $osf.trackClick('Preprints', 'navigate', 'navigate-to-preprints');
                        }}, 'View preprints'))
                    )
                ]
            )
        );
    }
};


module.exports = Preprints;
