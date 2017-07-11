/**
 * Prereg Challenge
 */

var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/meetings-and-conferences.css');

var Prereg = {
    view: function(ctrl) {
        return m('.p-v-sm',
            m('.row',
                [
                    m('.col-md-8',
                        [
                            m('div.conference-centering',  m('h3', 'See how preregistration can improve your next study.')),
                            m('div.conference-centering.m-t-lg',
                                m('p.text-bigger', 'Publish the results of your preregistered study for a chance to win $1,000.')
                            )
                        ]
                    ),
                    m('.col-md-4.text-center',
                        m('div',  m('a.btn.btn-banner.btn-success.btn-lg.btn-success-high-contrast.m-v-xl.f-w-xl', { type:'button',  href:'/prereg/', onclick: function() {
                            $osf.trackClick('prereg', 'navigate', 'navigate-to-begin-prereg');
                        }}, 'Preregister'))
                    )
                ]
            )
        );
    }
};


module.exports = Prereg;
