'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var widgetUtils = require('js/search_dashboard/widgetUtils');
var SearchWidgetPanel = require('js/search_dashboard/searchWidget');
var History = require('exports?History!history');
var utils = require('js/share/utils');
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
    self.vm.tempData = params.tempData;
    self.vm.widgetsToUpdate = [];
    self.vm.widgets = params.widgets;
    self.vm.widgetIds = [];
    for (var widget in self.vm.widgets) {
        if (self.vm.widgets.hasOwnProperty(widget)) {
            self.vm.widgetIds.push(widget);
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
            self.vm.requests[request] = widgetUtils.buildRequest(request, self.vm.requests[request],aggregations);
        }
    }
    self.vm.chartHandles = []; //TODO think about moving this...
    self.vm.results = null; //unused, only for backwards compatibility with utils TODO remove

    History.Adapter.bind(window, 'statechange', function(e) {
        var historyChanged = utils.updateHistory(self.vm);
        if (historyChanged){ widgetUtils.signalWidgetsToUpdate(self.vm, self.vm.widgetIds);}
    });

    //run dat shit
    searchDashboard.runRequests(self.vm, params.requestOrder);
};

searchDashboard.runRequest = function(vm, request, data){
    if (request.preRequest) {
        request.preRequest.forEach(function (funcToRun) {
            funcToRun(vm, request, data); //these are non pure functions...
        });
    }
    return m.request({
        method: 'post',
        background: true,
        data: utils.buildQuery(request),
        url: '/api/v1/search/'
    }).then(function (data) {
        if (request.postRequest) {
            request.postRequest.forEach(function (funcToRun) {
                funcToRun(vm, request, data);
            });
        }
    });
};

searchDashboard.runRequests = function(vm, requestOrder){
    requestOrder.forEach(function(parallelReqs){
        searchDashboard.recursiveRequest(vm, parallelReqs);
    });
};

searchDashboard.recursiveRequest = function(vm, requests, data){
    if (requests.length <= 0) {return; }
    var thisLevelReq = requests.shift();
    searchDashboard.runRequest(vm, vm.requests[thisLevelReq], data).then(function(newData){
        searchDashboard.recursiveRequest(vm, requests, newData);
    });
};

module.exports = searchDashboard;
