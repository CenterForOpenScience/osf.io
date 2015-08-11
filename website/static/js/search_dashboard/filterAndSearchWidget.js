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
    '_type' : 'Type is ',
    'contributors': 'Contributer is ',
    'date_created': 'Data Created is ',
    'tags': 'Tags contain '
};

function feildValueMappings(field, value, vm, widget){
    var fieldPretty = '';
    if (field[0] === 'date_created') {
        var valueParts = value.split(':');
        value = widgetUtils.timeSinceEpochInMsToMMYY(parseInt(valueParts[0])) +
            ' to ' + widgetUtils.timeSinceEpochInMsToMMYY(parseInt(valueParts[1]));
        fieldPretty = feildMappings[field[0]];
    } else if (field[0] === 'contributors' && field[1] === 'url') {
        var urlToNameMapper = widgetUtils.getGuidsToNamesMap([value], widget, vm);
        if (urlToNameMapper) {
            value = urlToNameMapper[value];
        }
        fieldPretty = feildMappings[field[0]];
    } else {
        fieldPretty = feildMappings[field[0]];
    }
    return fieldPretty + value;
}

function removeLockedFilters(filters) {
    return filters.filter(function(filt){
        var filtParts = filt.split('=');
            if (filtParts[1] === undefined){ //no lock, so ok to return
                return filtParts[0];
            }
    });
}

var ActiveFilters = {
    view : function(ctrl, params) {
        var vm = params.vm;

        var requiredFilters = removeLockedFilters(vm.requiredFilters);
        var optionalFilters = removeLockedFilters(vm.optionalFilters);

        var numFilters = requiredFilters.length + optionalFilters.length;
        if (numFilters <= 0){
            return m('p', {class: 'text-muted'}, 'No filters applied');
        }

        var requiredFilterViews = $.map(requiredFilters, function(searchFilter, i) {
            var isLastFilter = (i + 1 === numFilters);
            return m.component(Filter, $.extend({filter: searchFilter, isLastFilter: isLastFilter, required: true}, params));
        });

        var optionalFilterViews = $.map(optionalFilters, function(searchFilter, i) {
            var isLastFilter = (i + 1 + requiredFilters.length === numFilters);
            return m.component(Filter, $.extend({filter: searchFilter, isLastFilter: isLastFilter, required: false}, params));
        });

        return m('div', {}, requiredFilterViews.concat(optionalFilterViews));
    }
};

var Filter = {
    view : function(ctrl,params) {
        var vm = params.vm;
        var searchFilter = params.filter;
        var required = params.required;
        var isLastFilter = params.isLastFilter;
        var widget = params.widget;
        var filterParts = searchFilter.split(':');
        var field = filterParts[1].split('.');
        var value = filterParts.slice(2).join(':');
        return m('render-filter.m-t-xs.m-b-xs', [
            m('a.m-r-xs.m-l-xs', {
                onclick: function(event){
                    utils.removeFilter(vm, searchFilter);
                    widgetUtils.signalWidgetsToUpdate(vm, params.widget.thisWidgetUpdates);
                }
            }, [feildValueMappings(field, value, vm, widget), m('i.fa.fa-close.m-r-xs.m-l-xs')]),
            m('.badge.pointer',  isLastFilter ? ('') : (required ? 'AND' : 'OR'))
        ]);
    }
};

FilterAndSearchWidget.display = function(data, vm, widget){
    //results will always update regardless of callback location (no mapping)
    return m.component(ActiveFilters,{data: data, vm: vm, widget: widget});
};

module.exports = FilterAndSearchWidget;
