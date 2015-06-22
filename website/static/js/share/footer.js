var m = require('mithril');
var utils = require('./utils');
var MESSAGES = JSON.parse(require('raw!./messages.json'));

var Footer = {};

Footer.view = function(ctrl) {
    return m('', [
        m('.col-xs-12.col-lg-10.col-lg-offset-1',
            m('ul.provider-footer',
                {
                    style: {
                        'list-style-type': 'none'
                    }
                },
                ctrl.renderProviders()
            )
        ),
        m('.row', m('.col-md-12', {style: 'padding-top: 30px;'}, m('span', m.trust(MESSAGES.ABOUTSHARE))))
    ]);
};

Footer.controller = function(vm) {
    var self = this;
    self.vm = vm;

    self.renderProvider = function(result, index) {

        return m('li.provider-filter', {
                onclick: function(cb){
                    self.vm.query(self.vm.query() === '' ? '*' : self.vm.query());
                    self.vm.showFooter = false;
                    utils.updateFilter(self.vm, 'source:' + result.short_name);
                }
            },
            m('', [
                m('img', {
                    src: result.favicon,
                    style: {
                        width: '16px',
                        height: '16px'
                    }
                }), ' ',
                result.long_name]
             )
        );
    };

    self.renderProviders = function() {
        return self.vm.showFooter ? $.map(self.vm.sortProviders(), self.renderProvider) : null;
    };
};

module.exports = Footer;
