'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var widgetUtils = require('js/search_dashboard/widgetUtils');
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
searchDashboard.view = function (ctrl, params) {
    var grid = [];
    params.rowMap.forEach(function(row) {
        grid.push(m('.row', {}, row.map(function (widgetName) {
            return m.component(SearchWidget, {
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
        return m.component(SearchWidget, {
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
        var historyChanged = searchUtils.hasRequestStateChanged(self.vm);
        if (historyChanged){
            widgetUtils.signalWidgetsToUpdate(self.vm, self.vm.widgetIds);
            searchUtils.updateRequestsFromHistory(self.vm);
        }
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

require('css/search_widget.css');

function loadingIcon(){
    return m('.spinner-loading-wrapper', [
            m('.logo-spin.text-center', [
                m('img[src=/static/img/logo_spin.png][alt=loader]')
            ]),
            m('p.m-t-sm.fg-load-message', ' Loading... ')
        ]);
}

var SearchWidget = {
    /**
     * View function for a search widget panel. Returns search widget nicely wrapped in panel with minimize actions.
     *
     * @param {Object} ctrl: controller object automatically passed in by mithril
     * @param {Object} params: params containing vm
     * @return {object}  initialised SearchWidget component
     */
    view : function (ctrl, params) {
        var dataReady = params.widget.display.reqRequests.every(function(req){
            return params.vm.requests[req].complete();
        });

        return m(params.widget.size[0], {},
            m('.panel.panel-default', {}, [
                m('.panel-heading clearfix', {},[
                    m('h3.panel-title',params.widget.title),
                    m('.pull-right', {},
                        m('a.widget-expand', {onclick: function () {
                                ctrl.hidden(!ctrl.hidden());
                                m.redraw(true);
                            }},
                            ctrl.hidden() ? m('i.fa.fa-angle-up') : m('i.fa.fa-angle-down')
                        )
                    )
                ]),
                m('.panel-body', {style: ctrl.hidden() ? 'display:none' : ''},
                    dataReady ? m.component(params.widget.display.component, params) : loadingIcon())
            ])
        );
    },

    /**
     * controller function for a search widget panel. Initialises component.
     */
    controller : function(params) {
        this.hidden = m.prop(false);
    }
};

module.exports = searchDashboard;
