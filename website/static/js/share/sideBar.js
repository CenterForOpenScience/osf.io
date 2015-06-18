var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('./utils');

var SideBar = {};

SideBar.view = function(ctrl){
    if (ctrl.vm.results === null){
        return [];
    }
    return m('', [
            m('.sidebar-header',  ['Active filters:',
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
            m('.sidebar-header', 'Providers:'),
            m('ul', {style:{'list-style-type': 'none', 'padding-left': 0}}, ctrl.renderProviders()),
    ]);
};

SideBar.controller = function(vm) {
    var self = this;
    self.vm = vm;

    self.vm.sortMap = {
        'Date': 'dateUpdated',
        Relevance: null
    };

    self.renderSort = function(){
        return $.map(Object.keys(self.vm.sortMap), function(a) {
            return m('li',
                m('a', {
                    'href': '#',
                    onclick: function(event) {
                        self.vm.sort(a);
                        utils.search(self.vm);
                    }
                }, a));
        });
    };

    self.renderFilters = function(){
        return $.map(self.vm.optionalFilters.concat(self.vm.requiredFilters), function(filter){
            return m('li.render-filter', [
                m('a', {
                    onclick: function(event){
                        utils.removeFilter(self.vm, filter);
                    }
                }, [m('i.fa.fa-close'), ' ' + filter
                ])
            ]);
        });
    };

    self.renderProvider = function(result, index) {
        var checked = (self.vm.optionalFilters.indexOf('source:' + result.short_name) > -1 || self.vm.requiredFilters.indexOf('source:' + result.short_name) > -1) ? 'in-filter' : '';

        return m('li',
            m('.provider-filter', {
                'class': checked,
                onclick: function(cb){
                    if (checked === 'in-filter') {
                        utils.removeFilter(self.vm, 'source:' + result.short_name);
                    } else {
                        utils.updateFilter(self.vm, 'source:' + result.short_name);
                    }
                }
            }, [
                m('img', {src: result.favicon, style: {height:'16px', width:'16px'}}), ' ', result.long_name
            ])
        );

    };

    self.vm.sortProviders = function() {
        return $.map(Object.keys(self.vm.ProviderMap), function(result, index){
            return self.vm.ProviderMap[result];
        }).sort(function(a,b){
                return a.long_name.toUpperCase() > b.long_name.toUpperCase() ? 1: -1;
        });
    };

    self.renderProviders = function () {
        return $.map(self.vm.sortProviders(), self.renderProvider);
    };

};


module.exports = SideBar;
