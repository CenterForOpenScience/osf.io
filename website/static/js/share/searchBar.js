var m = require('mithril');
var $osf = require('osfHelpers');
var utils = require('./utils.js');

var SearchBar = {};


SearchBar.view = function(ctrl) {
    return [
        m('.row', [
            m('.col-md-12', {
                    style: {
                        margin: 'auto',
                        display: 'block',
                        'text-align': 'center'
                    }
            }, [
                m('img[src=/static/img/share-logo-icon.png]', {
                    style: {
                        height: 'auto',
                        'max-width': '15%',
                        '-webkit-animation-duration': '3s'
                    },
                    // class: 'animated pulse'
                }),
                m('span.about-share-header', 'SHARE'),
                m('div', {style: {color: 'darkgrey'}}, m('small', [
                    'Notice: this is a public alpha release'
                ])),
                m('br'),
            ])
        ]),
        m('.row', [
            m('.col-md-12', [
                m('form.input-group', {
                    onsubmit: ctrl.search,
                },[
                    m('input.share-search-input.form-control[type=text][placeholder=Search][autofocus]', {
                        value: ctrl.vm.query(),
                        onchange: m.withAttr('value', ctrl.vm.query),
                    }),
                    m('span.input-group-btn', [
                        m('button.btn.osf-search-btn', m('i.icon-search.icon-lg')),
                    ])
                ])
            ])
        ])
    ];
};


SearchBar.controller = function(vm) {
    var self = this;

    self.vm = vm;

    self.vm.totalCount = 0;
    self.vm.providers = 26;
    self.vm.latestDate = undefined;
    self.vm.showStats = true;

    self.search = function(e) {
        utils.maybeQuashEvent(e);
        utils.search(self.vm);
    };

    self.search();
};


module.exports = SearchBar;
