var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/meetings-and-conferences.css');

var PreregBanner = {
    view: function(ctrl) {
        return m('.p-v-sm',
            m('.row.prereg-banner',
                [
                    m('.col-md-9.m-v-sm',
                        [
                            m('div.conference-centering',
                                m('p', 'Improve your next study. Enter the Prereg Challenge and you could win $1,000.')
                            )
                        ]
                    ),
                    m('.col-md-3.text-center.m-v-sm',
                        m('div',  m('a.btn.btn-success.btn-success-high-contrast.f-w-xl', { type:'button',  href:'/prereg/', onclick: function() {
                            $osf.trackClick('prereg', 'navigate', 'navigate-to-begin-prereg');
                        }}, 'Start Prereg Challenge'))
                    )
                ]
            )
        );
    }
};

module.exports = PreregBanner;
