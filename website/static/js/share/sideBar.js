var m = require('mithril');
var $osf = require('osfHelpers');
var utils = require('./utils.js');

var SideBar = {};

SideBar.view = function(ctrl){
    if (ctrl.vm.results === null){
        return [];
    }
    return m('.row', [
        m('.btn-group', [
            m('button.btn.btn-default.dropdown-taggle', {
                    'data-toggle': 'dropdown',
                    'aria-expanded': 'false'
                }, ['Sort by: ' + ctrl.vm.sort(), m('span.caret')]
            ),
            m('ul.dropdown-menu', {'role': 'menu'}, [
                m('li', [m('a', {
                    'href': '#',
                    onclick: function(event) {
                            ctrl.vm.sort('Relevance');
                            utils.search(ctrl.vm);
                        }
                }, ['Relevance'])]),
                m('li', [m('a', {
                    'href': '#',
                    onclick: function(event) {
                        ctrl.vm.sort('Date');
                        utils.search(ctrl.vm);
                    }
                }, ['Date'])]),
            ])
        ]),
        m('br'),
        m('ul', {style:{'list-style-type': 'none'}}, ctrl.renderProviders()),
    ]);
};

SideBar.controller = function(vm) {
    var self = this;
    self.vm = vm;

    self.vm.sort = m.prop($osf.urlParams().sort) || m.prop("Relevance");
    self.vm.requiredFilters = $osf.urlParams.required ? $osf.urlParams().required.split('|') : [];
    self.vm.optionalFilters = $osf.urlParams().optional ? $osf.urlParams().optional.split('|') : [];

    self.renderProviders = function () {
        return Object.keys(self.vm.ProviderMap).map(function(result, index){
            return self.vm.ProviderMap[result];
        }).sort(function(a,b){
                return a.long_name > b.long_name ? 1: -1;
        }).map(function(result, index){
            return m('li', [m('label', [
                m('input', {
                    'type': 'checkbox',
                    'checked': (self.vm.optionalFilters.indexOf('source:' + result.short_name) > -1),
                    onclick: function(cb){
                        if (cb.target.checked == true){
                            utils.updateFilter(self.vm, 'source:' + result.short_name);
                        } else {
                            utils.removeFilter(self.vm, 'source:' + result.short_name);
                        }
                    }
                }),
                ' ' + result.long_name
            ])])
        });
    };
};


module.exports = SideBar;
