var m = require('mithril');
var $osf = require('osfHelpers');
var utils = require('./utils.js');

var SearchBar = {};


SearchBar.view = function(ctrl) {
    return [
        m('.row', [
            m('.col-md-12', [
                m('img[src=/static/img/share-logo-icon.png]', {
                    style: {
                        margin: 'auto',
                        height: 'auto',
                        display: 'block',
                        'max-width': '40%',
                        '-webkit-animation-duration': '3s'
                    },
                    class: 'animated pulse'
                }),
                m('br')
            ])
        ]),
        m('.row', [
            m('.col-md-12', [
                m('form.input-group', {
                    onsubmit: ctrl.search,
                },[
                    m('input.share-search-input.form-control[type=text][placeholder=Discover][autofocus]', {
                        value: ctrl.vm.query(),
                        onchange: m.withAttr('value', ctrl.vm.query),
                    }),
                    m('span.input-group-btn', [
                        m('button.btn.osf-search-btn', m('i.icon-circle-arrow-right.icon-lg')),
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
