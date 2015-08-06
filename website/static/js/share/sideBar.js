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
        var new_params = {vm: vm};
        return m('', [
                m.component(ActiveFiltersHeader, new_params),
                m.component(ActiveFilters, new_params),
                m.component(ProviderList, new_params)
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
                // Strip out all the extra information from the filter string, for nice
                // human friendly viewing.
                var filter_parts = filter.split(':');
                var field = filter_parts[1].split('.').slice(-1);
                var value = filter_parts.slice(2).join(':');
                var pretty_string = [field, value].join(':');

                return m('li.render-filter', [
                    m('a', {
                        onclick: function(event){
                            utils.removeFilter(vm, filter);
                        }
                    }, [m('i.fa.fa-close'), ' ' + pretty_string
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
                m('img.provider-favicon', {src: provider.favicon, alt: 'favicon for ' + provider.long_name}), ' ', provider.long_name
            ])
        );
    }
};

module.exports = SideBar;
