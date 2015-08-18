'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var widgetUtils = require('js/search_dashboard/widgetUtils');
var SearchWidgetPanel = require('js/search_dashboard/searchWidget');
var History = require('exports?History!history');
var searchUtils = require('js/search_dashboard/searchUtils');
var searchDashboard = {};

/**
 * View function for the search dashboard. Gridifys the contained
 * widgets depending on their row.
 *
 * @param {Object} ctrl: controller object automatically passed in by mithril
 * @return {m.component object}  initialised searchDashboard component
 */
searchDashboard.view = function (ctrl, params, children) {
    var grid = [];
    params.rowMap.forEach(function(row) {
        grid.push(m('.row', {}, row.map(function (widgetName) {
            return m.component(SearchWidgetPanel, {
                key: widgetName,
                widget: ctrl.vm.widgets[widgetName],
                vm: ctrl.vm
            });
        })));
    });
    return m('.col-lg-12', {} ,grid);

};

searchDashboard.returnRow = function(widgetNames, vm){
    widgetNames.map(function(widgetName){
        return m.component(SearchWidgetPanel, {
            key: vm.widgets[widgetName].id,
            widget: vm.widgets[widgetName],
            vm: vm});
    });
};


searchDashboard.vm = {};

/**
 * controller function for a search Dashboard component.
 * Setups vm for dashboard, elastic searches, and params for widgets
 *
 * @return {m.component.controller}  returns itself
 */
searchDashboard.controller = function (params) {
    var self = this;
    //search dashboard state
    self.widgets = params.widgets || [];
    self.error = m.prop('');
    self.rows = params.rows;

    //search model state
    self.vm = searchDashboard.vm;
    self.vm.requestOrder = params.requestOrder;
    self.vm.tempData = params.tempData;
    self.vm.widgetsToUpdate = [];
    self.vm.widgets = params.widgets;
    self.vm.widgetIds = [];
    for (var widget in self.vm.widgets) {
        if (self.vm.widgets.hasOwnProperty(widget)) {
            self.vm.widgetIds.push(widget);
            self.vm.widgets[widget].filters = {};
        }
    }

    //Build requests
    self.vm.requests = params.requests;
    for (var request in self.vm.requests) {
        if (self.vm.requests.hasOwnProperty(request)) {
            var aggregations = [];
            for (var widget in self.vm.widgets) {
                if (self.vm.widgets.hasOwnProperty(widget)) {
                    if(self.vm.widgets[widget].aggregations) {
                        if (self.vm.widgets[widget].aggregations[request]) {
                            aggregations.push(self.vm.widgets[widget].aggregations[request]);
                        }
                    }
                }
            }
            self.vm.requests[request] = searchDashboard.buildRequest(request, self.vm.requests[request],aggregations);
        }
    }
    self.vm.chartHandles = []; //TODO think about moving this...
    self.vm.results = null; //unused, only for backwards compatibility with utils TODO remove

    History.Adapter.bind(window, 'statechange', function(e) {
        var historyChanged = searchUtils.updateHistory(self.vm);
        if (historyChanged){ widgetUtils.signalWidgetsToUpdate(self.vm, self.vm.widgetIds);}
    });

    //run dat shit
    searchUtils.runRequests(self.vm);
};

searchDashboard.buildRequest = function(id, request, aggs){
    return {
        id : id,
        elasticURL: request.elasticURL,
        query: request.query || m.prop('*'),
        optionalFilters : request.optionalFilters || [],
        requiredFilters : request.requiredFilters || [],
        preRequest: request.preRequest,
        postRequest: request.postRequest,
        aggregations : aggs || [],
        size: request.size,
        page: request.page,
        data: null,
        formattedData: {},
        complete: m.prop(false),
        sort: m.prop(request.sort),
        sortMap: request.sortMap
    };
};

module.exports = searchDashboard;
