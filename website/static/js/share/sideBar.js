var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('./utils');


var SideBar = {
    view: function(ctrl, params){
        var vm = params.vm;
        if (vm.results === null){
            return [];
        }
        var ad_params = {vm: vm};
        return m('', [
                m.component(ActiveFiltersHeader, ad_params),
                m.component(ActiveFilters, ad_params),
                m.component(ProviderList, ad_params)
        ]);
    },
};

var ActiveFiltersHeader = {
    view: function(ctrl, params) {
        var vm = params.vm;

        return m('.sidebar-header',  ['Active filters:',
            (vm.optionalFilters.length > 0 || vm.requiredFilters.length > 0) ? m('a', {
                style: {
                    'float': 'right'
                }, onclick: function(event){
                    vm.optionalFilters = [];
                    vm.requiredFilters = [];
                    utils.search(vm);
                    }
            }, ['Clear ', m('i.fa.fa-close')]) : []]);
    }
};


var ActiveFilters = {
    view: function(ctrl, params){
        var vm = params.vm;

        return m('ul.unstyled',
            $.map(vm.optionalFilters.concat(vm.requiredFilters), function(filter){
                return m('li.render-filter', [
                    m('a', {
                        onclick: function(event){
                            utils.removeFilter(vm, filter);
                        }
                    }, [m('i.fa.fa-close'), ' ' + filter.split(':').slice(1).join(':')
                    ])
                ]);
        }));

    }
};

var ProviderList = {
    view: function (ctrl, params) {
        var vm = params.vm;
        return m('', [
            m('.sidebar-header', 'Providers:'),
            m('ul.unstyled', $.map(vm.sortProviders(), function(provider, index) {
                return m.component(Provider, {vm: vm, provider: provider});
            }))
        ]);
    }
};

var Provider = {
    view: function(ctrl, params) {
        var vm = params.vm;
        var provider = params.provider;
        var checked = (vm.optionalFilters.concat(vm.requiredFilters).indexOf('match:shareProperties.source:' + provider.short_name) > -1) ? 'in-filter' : '';

        return m('li',
            m('.provider-filter.break-word', {
                'class': checked,
                onclick: function(cb){
                    if (checked === 'in-filter') {
                        utils.removeFilter(vm, 'match:shareProperties.source:' + provider.short_name);
                    } else {
                        utils.updateFilter(vm, 'match:shareProperties.source:' + provider.short_name);
                    }
                }
            }, [
                m('img.provider-favicon', {src: provider.favicon}), ' ', provider.long_name
            ])
        );

    }
};

module.exports = SideBar;
