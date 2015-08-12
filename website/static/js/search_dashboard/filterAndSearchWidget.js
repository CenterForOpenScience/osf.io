'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
require('truncate');
var FilterAndSearchWidget = {};

var fieldMappings = {
    '_type' : 'Type is ',
    'contributors': ' is a Contributor',
    'date_created': 'Data Created is ',
    'tags': 'Tags contain '
};

/**
 * Removes any filters containing the '=lock' extension
 *
 * @param {Array} field: array containing the names of elastic field that is being filtered
 * @param {String/Int} value: filter parameters in string or int form
 * @param {Object} vm: Search Dashboard vm
 * @param {Object} widget: filter and search widget, so flag can be set for searching
 * @return {string}  Array of filters with locked filters removed
 */
function fieldValueMappings(field, value, vm, widget){ //TODO would like to refactor so the widget is not required here...
    var fieldPretty = '';
    if (field[0] === 'date_created') {
        var valueParts = value.split(':');
        value = widgetUtils.timeSinceEpochInMsToMMYY(parseInt(valueParts[0])) +
            ' to ' + widgetUtils.timeSinceEpochInMsToMMYY(parseInt(valueParts[1]));
        fieldPretty = fieldMappings[field[0]];
    } else if (field[0] === 'contributors' && field[1] === 'url') {
        var url = value.replace(/\//g, '');
        var urlToNameMapper = widgetUtils.getGuidsToNamesMap([url], widget, vm);
        if (urlToNameMapper) {
            value = urlToNameMapper[url];
        }
        fieldPretty = fieldMappings[field[0]];
        return value + fieldPretty;
    } else {
        fieldPretty = fieldMappings[field[0]];

    }
    return fieldPretty + value;
}

/**
 * Removes any filters containing the '=lock' extension
 *
 * @param {Array} filters: Array of filters to removed locked filters from
 * @return {Array}  Array of filters with locked filters removed
 */
function removeLockedFilters(filters) {
    return filters.filter(function(filt){
        var filtParts = filt.split('=');
            if (filtParts[1] === undefined){ //no lock, so ok to return
                return filtParts[0];
            }
    });
}


var ActiveFilters = {
    /**
     * View function of ActiveFilters component
     *
     * @param {Object} ctrl: passed by mithril, emtpy controller for object
     * @param {Object} params: mithril passed arg with vm, and widget information
     * @return {Object}  div containing all (non-locked) filters
     */
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
    /**
     * View function of Filter component
     *
     * @param {Object} ctrl: passed by mithril, emtpy controller for object
     * @param {Object} params: mithril passed arg with vm, filter and widget information
     * @return {Object}  div for display of filter
     */
    view : function(ctrl, params) {
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
            }, [fieldValueMappings(field, value, vm, widget), m('i.fa.fa-close.m-r-xs.m-l-xs')]),
            m('.badge.pointer',  isLastFilter ? ('') : (required ? 'AND' : 'OR'))
        ]);
    }
};

/**
 * View function of Filter component
 *
 * @param {Object} ctrl: passed by mithril, emtpy controller for object
 * @param {Object} params: mithril passed arg with vm, filter and widget information
 * @return {Object}  div for display of filter
 */
var Search = {
    view: function(ctrl, params){
        return null; //TODO
    }    
};

/**
 * Entry point for this widget, returns instantiated ActiveFilters and Search Widget
 * TODO @bdyetton this is actually unnecessary ;level of wrapping, components could be created in the search widget class
 *
 * @param {Object} data: data to populate widget with (not used by this function)
 * @param {Object} vm: view model for Search Dashboard
 * @return {Object}  widget: widget information for the filter and search widget
 */
FilterAndSearchWidget.display = function(data, vm, widget){
    //results will always update regardless of callback location (no mapping)
    return m.component(ActiveFilters,{data: data, vm: vm, widget: widget});
};

module.exports = FilterAndSearchWidget;
