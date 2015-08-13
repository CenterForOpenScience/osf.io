var m = require('mithril');
var utils = require('./utils');
var MESSAGES = JSON.parse(require('raw!./messages.json'));

var Footer = {
    view: function(ctrl, params) {
        return m('', [
            m('.row', m('.col-xs-12.col-lg-10.col-lg-offset-1', m.component(ProviderList, params))),
            m('.row', m('.col-md-12', {style: {paddingTop: '30px'}}, m('span', m.trust(MESSAGES.ABOUTSHARE))))
        ]);
    }
};

var ProviderList = {
    view: function(ctrl, params) {
        var vm = params.vm;
        return m('ul.provider-footer', vm.showFooter ? $.map(vm.sortProviders(), function(provider, index) {
            return m.component(Provider, {vm: vm, provider: provider});
        }) : null);
    }
};

var Provider = {
    view: function(ctrl, params) {
        var vm = params.vm;
        var provider = params.provider;
        return m(
            'li.provider-filter', [
                m('a.provider-filter', {
                    href: '#',
                    onclick: function(cb){
                        vm.query(vm.query() === '' ? '*' : vm.query());
                        vm.showFooter = false;
                        utils.updateFilter(vm, 'match:shareProperties.source:' + provider.short_name);
                    }
                }, [
                    m('img.provider-favicon', {
                        src: provider.favicon,
                        alt: 'favicon for ' + provider.long_name
                    }), ' ',
                    provider.long_name
                ])
        ]);
    }
};

module.exports = Footer;
