'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var searchUtils = require('js/search_dashboard/searchUtils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
require('truncate');

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

var FilterWidget = {
    /**
     * View function of ActiveFilters component
     *
     * @param {Object} ctrl: passed by mithril, emtpy controller for object
     * @param {Object} params: mithril passed arg with vm, and widget information
     * @return {Object}  div containing all (non-locked) filters
     */
    view : function(ctrl, params) {
        var vm = params.vm;
        var widget = params.widget;
        var requiredFilters = removeLockedFilters(vm.requests[widget.display.reqRequests[0]].requiredFilters);
        var optionalFilters = removeLockedFilters(vm.requests[widget.display.reqRequests[0]].optionalFilters);

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
        var fields = filterParts[1].split('.');
        var values = filterParts.slice(2);

        return m('render-filter.m-t-xs.m-b-xs', [
            m('a.m-r-xs.m-l-xs', {
                onclick: function(event){
                    searchUtils.removeFilter(vm,[], searchFilter);
                    widgetUtils.signalWidgetsToUpdate(vm, params.widget.display.callbacksUpdate);
                }
            }, widget.display.filterParsers[filterParts[0]](fields, values, vm, widget), m('i.fa.fa-close.m-r-xs.m-l-xs')),
            m('.badge.pointer',  isLastFilter ? ('') : (required ? 'AND' : 'OR'))
        ]);
    }
};

module.exports = FilterWidget;
