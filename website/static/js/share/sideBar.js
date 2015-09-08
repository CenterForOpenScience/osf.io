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
        var newParams = {vm: vm};
        return m('.sidebar', [
                m.component(ActiveFiltersHeader, newParams),
                m.component(ActiveFilters, newParams),
                m.component(ProviderList, newParams)
        ]);
    },
};

var ActiveFiltersHeader = {
    view: function(ctrl, params) {
        var vm = params.vm;

        return m('.sidebar-header', (vm.optionalFilters.length > 0 || vm.requiredFilters.length > 0) ? ['Active filters:',
             m('a', {
                style: {
                    'float': 'right'
                }, onclick: function(event){
                    vm.optionalFilters = [];
                    vm.requiredFilters = [];
                    utils.search(vm);
                    }
            }, ['Clear ', m('i.fa.fa-close')])
        ]:[]);
    }
};


var ActiveFilters = {
    view: function(ctrl, params){
        var vm = params.vm;
        var filters = vm.optionalFilters.concat(vm.requiredFilters);

        return (filters.length > 0) ? m('ul.unstyled',
            $.map(filters, function(filter){
                // Strip out all the extra information from the filter string, for nice
                // human friendly viewing.
                var filterParts = filter.split(':');
                var field = filterParts[1].split('.').slice(-1);
                var value = filterParts.slice(2).join(':');
                var prettyString = [field, value].join(':');

                return m('li.render-filter', [
                    m('a', {
                        onclick: function(event){
                            utils.removeFilter(vm, filter);
                        }
                    }, [m('i.fa.fa-close'), ' ' + prettyString
                    ])
                ]);
        })) : m('');

    }
};

var ProviderList = {
    view: function (ctrl, params) {
        var vm = params.vm;
        return m('.provider-list', [
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
            m('a.provider-filter.break-word', {
                'class': checked,
                onclick: function(cb){
                    if (checked === 'in-filter') {
                        utils.removeFilter(vm, 'match:shareProperties.source:' + provider.short_name);
                    } else {
                        utils.updateFilter(vm, 'match:shareProperties.source:' + provider.short_name);
                    }
                }
            }, [
                m('img.provider-favicon', {src: provider.favicon, alt: 'favicon for ' + provider.long_name}), ' ', provider.long_name
            ])
        );
    }
};

module.exports = SideBar;
