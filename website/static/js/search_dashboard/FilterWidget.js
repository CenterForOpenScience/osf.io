'use strict';

var pd = require('pretty-data').pd;
var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var searchUtils = require('js/search_dashboard/searchUtils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
require('truncate');

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
        var ANDFilters = vm.requests[widget.display.reqRequests[0]].userDefinedANDFilters;
        var ORFilters = vm.requests[widget.display.reqRequests[0]].userDefinedORFilters;

        var numFilters = ANDFilters.length + ORFilters.length;
        if (numFilters <= 0){
            return m('p', {class: 'text-muted'}, 'No filters applied');
        }

        var ANDFilterViews = $.map(ANDFilters, function(searchFilter, i) {
            var isLastFilter = (i + 1 === numFilters);
            return m.component(Filter, $.extend({},params,{key: searchFilter, filter: searchFilter, isLastFilter: isLastFilter, required: true}));
        });

        var ORFilterViews = $.map(ORFilters, function(searchFilter, i) {
            var isLastFilter = (i + 1 + ANDFilters.length === numFilters);
            return m.component(Filter, $.extend({},params,{key: searchFilter, filter: searchFilter, isLastFilter: isLastFilter, required: false}));
        });
        return m('div', {}, ANDFilterViews.concat(ORFilterViews));
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

        return m('render-filter.m-t-xs.m-b-xs', {}, [
            m('a.m-r-xs.m-l-xs', {
                onclick: function(event){
                    widgetUtils.signalWidgetsToUpdate(vm, params.widget.display.callbacksUpdate);
                    searchUtils.removeFilter(vm,[], searchFilter);
                }
            }, widget.display.filterParsers[filterParts[0]](fields, values, vm, widget), m('i.fa.fa-close.m-r-xs.m-l-xs')),
            m('.badge.pointer',  isLastFilter ? ('') : (required ? 'AND' : 'OR'))
        ]);
    }
};

module.exports = FilterWidget;
