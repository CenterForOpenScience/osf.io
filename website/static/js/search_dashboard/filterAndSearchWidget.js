'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
require('truncate');
var FilterAndSearchWidget = {};

var feildMappings = {
    '_type' : 'Type',
    'url' : 'Contributer',
    'date_created' : 'Data Created'
};

function feildValueMappings(field, value){
    if (field === 'date_created') {
        var valueParts = value.split(':');
        value = widgetUtils.timeSinceEpochInMsToMMYY(parseInt(valueParts[0])) +
            ' to ' + widgetUtils.timeSinceEpochInMsToMMYY(parseInt(valueParts[1]));
    }
    return feildMappings[field] + ' is ' + value;
}

var ActiveFilters = {
    view : function(ctrl, params) {
        var vm = params.vm;
            if ((vm.requiredFilters.length <= 0) && (vm.optionalFilters.length <= 0)){
                return m('p', {class: 'text-muted'}, 'No filters applied');
            }
            var numFilters = vm.requiredFilters.length + vm.optionalFilters.length;
            var requiredFilterViews = $.map(vm.requiredFilters, function(filter, i) {
                var lastFilter = (i + 1 === numFilters);
                return m.component(Filter, $.extend({filter: filter, lastFilter: lastFilter, required: true}, params));
            });
            var optionalFilterViews = $.map(vm.optionalFilters, function(filter, i) {
                var lastFilter = (i + 1 + vm.requiredFilters.length === numFilters);
                return m.component(Filter, $.extend({filter: filter, lastFilter: lastFilter, required: false}, params));
            });
            return m('div', {}, requiredFilterViews.concat(optionalFilterViews));
    }
};

var Filter = {
    view : function(ctrl,params) {
        var vm = params.vm;
        var filter = params.filter;
        var required = params.required;
        var lastFilter = params.lastFilter;
        var filterParts = filter.split(':');
        var field = filterParts[1].split('.').slice(-1);
        var value = filterParts.slice(2).join(':');
        return m('render-filter.m-t-xs.m-b-xs', [
            m('a.m-r-xs.m-l-xs', {
                onclick: function(event){
                    utils.removeFilter(vm, filter);
                    widgetUtils.signalWidgetsToUpdate(vm, params.widget.thisWidgetUpdates);
                }
            }, [feildValueMappings(field[0], value), m('i.fa.fa-close.m-r-xs.m-l-xs')]),
            m('.badge.pointer',  lastFilter ? ('') : (required ? 'AND' : 'OR'))
        ]);
    }
};

FilterAndSearchWidget.display = function(data, vm, widget){
    //results will always update regardless of callback location (no mapping)
    return m.component(ActiveFilters,{data: data, vm: vm, widget: widget});
};

module.exports = FilterAndSearchWidget;
