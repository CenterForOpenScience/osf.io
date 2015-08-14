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
    var row;
    for(row = 1; row <= ctrl.rows; row++){
        grid.push(m('.row',{},ctrl.widgets.map(function(widget) {
            if (widget.row === row) {
                return m.component(SearchWidgetPanel, {key: widget.id, widget: widget, vm: ctrl.vm});
            }
        })));
    };
    return m('.col-lg-12', {} ,grid);

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
    self.vm.widgetIds = [];
    if (self.widgets){
        self.widgets.forEach(function(widget){
            self.vm.widgetIds.push(widget.id);
        });
    }
    //Build requests
    self.vm.requests = {};
    if (self.requests){
        self.requests.forEach(function(req){
            var aggregations = [];
            self.widgets.forEach(function(widget){
                if (widget.aggregation[req.id]){
                    aggregations.push(widget.aggregation[req.id]);
                }
            });
            var item = {};
            item[req.id] = widgetUtils.buildRequest(req.id, req, aggregations);
            self.vm.requests = $.extend(self.vm.requests, item);
        });
    }
    self.vm.chartHandles = []; //TODO think about moving this...
    self.vm.results = null; //unused, only for backwards compatibility with utils TODO remove

    History.Adapter.bind(window, 'statechange', function(e) {
        var historyChanged = utils.updateHistory(self.vm);
        if (historyChanged){ widgetUtils.signalWidgetsToUpdate(self.vm, self.vm.widgetIds);}
    });
};

module.exports = searchDashboard;
