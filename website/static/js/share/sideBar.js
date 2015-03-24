var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('./utils.js');

var SideBar = {};

SideBar.view = function(ctrl){
    if (ctrl.vm.results === null){
        return [];
    }
    return m('', [
            m('.sidebarHeader',  ['Active filters:',
              (ctrl.vm.optionalFilters.length > 0 || ctrl.vm.requiredFilters.length > 0) ? m('a', {
                  style: {
                      'float': 'right'
                  }, onclick: function(event){
                      ctrl.vm.optionalFilters = [];
                      ctrl.vm.requiredFilters = [];
                      utils.search(ctrl.vm);
                    }
              }, ['Clear ', m('i.fa.fa-close')]) : []]),
            m('ul', {style:{'list-style-type': 'none', 'padding-left': 0}}, ctrl.renderFilters()),
            m('.sidebarHeader', 'Providers:'),
            m('ul', {style:{'list-style-type': 'none', 'padding-left': 0}}, ctrl.renderProviders()),
    ]);
};

SideBar.controller = function(vm) {
    var self = this;
    self.vm = vm;

    self.vm.sort = $osf.urlParams().sort ? m.prop($osf.urlParams().sort) : m.prop("Relevance");
    self.vm.requiredFilters = $osf.urlParams().required ? $osf.urlParams().required.split('|') : [];
    self.vm.optionalFilters = $osf.urlParams().optional ? $osf.urlParams().optional.split('|') : [];

    self.vm.sortMap = {
        'Date': 'dateUpdated',
        Relevance: null
    };

    self.renderSort = function(){
        return Object.keys(self.vm.sortMap).map(function(a) {
            return m('li',
                m('a', {
                    'href': '#',
                    onclick: function(event) {
                        self.vm.sort(a);
                        utils.search(self.vm);
                    }
                }, a))
        });
    };

    self.renderFilters = function(){
        return self.vm.optionalFilters.concat(self.vm.requiredFilters).map(function(filter){
            return m('li.renderFilter', [
                m('a', {
                    onclick: function(event){
                        utils.removeFilter(self.vm, filter)
                    }
                }, [m('i.fa.fa-close'), ' ' + filter
                ])
            ])
        });
    };

    self.renderProviders = function () {
        return Object.keys(self.vm.ProviderMap).map(function(result, index){
            return self.vm.ProviderMap[result];
        }).sort(function(a,b){
                return a.long_name > b.long_name ? 1: -1;
        }).map(function(result, index){
            var checked = (self.vm.optionalFilters.indexOf('source:' + result.short_name) > -1 || self.vm.requiredFilters.indexOf('source:' + result.short_name) > -1) ? 'inFilter' : '';

            return m('li', m('.providerFilter', {
                    'class': checked,
                    onclick: function(cb){
                        if (checked === 'inFilter') {
                            utils.removeFilter(self.vm, 'source:' + result.short_name);
                        } else {
                            utils.updateFilter(self.vm, 'source:' + result.short_name);
                        }
                    }
                }, result.long_name
            ));
        });
    };
};


module.exports = SideBar;
