'use strict';
//Defines a template for a basic search widget
var m = require('mithril');
var History = require('exports?History!history');

var widgetUtils = require('js/search_dashboard/widgetUtils');
var searchUtils = require('js/search_dashboard/searchUtils');

require('./css/search-widget.css');

var searchDashboard = {};


searchDashboard.mount = function(divId, params){
    var component = {
        view: function(ctrl)
        {
            return m.component(searchDashboard, params);
        }
    }
    m.mount(divId, component);
};
/**
 * View function for the search dashboard. Gridifys the contained
 * widgets depending on their row (in rowmap).
 *
 * @param {Object} ctrl: controller object automatically passed in by mithril
 * @return {Object}  initialised searchDashboard component
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

/*populates a row with widgets*/
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
    if (params.url){
        params.url = JSON.parse(decodeURIComponent(params.url).substring(1));
    } else {
        params.url = {};
    }
    //search model state
    self.vm = searchDashboard.vm;
    self.vm.loadingIcon = params.loadingIcon || function(){return m('div',' Loading... '); };
    self.vm.errorHandlers = params.errorHandlers;
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
            self.vm.requests[request] = searchDashboard.buildRequest(request, self.vm.requests[request], params.url, aggregations);
        }
    }

    //add hook to history
    History.Adapter.bind(window, 'statechange', function(e) {
        var historyChanged = searchUtils.hasRequestsStateChanged(self.vm);
        if (historyChanged){
            widgetUtils.signalWidgetsToUpdate(self.vm, self.vm.widgetIds);
            searchUtils.updateRequestsFromHistory(self.vm);
        }
    });

    //run dat shit
    searchUtils.runRequests(self.vm);
};

/**
 * Builds a request object based on the current URL and user defined inputs or defaults
 *
 * @param {string} id: name of request
 * @param {object} userRequestParams: user defined params to override request default params, can be {}
 * @param {object} currentUrl: user defined params to override request default params, can be {}
 * @param {Array} aggs: user defined aggregations to add to this query, can be []
 * @return {object}  initialised Request object
 */
searchDashboard.buildRequest = function(id, userRequestParams, currentUrl, aggs){
    var requestURL = currentUrl[id] || {};
    var ANDFilters = [];
    var ORFilters = [];
    if (requestURL.ANDFilters) {
        ANDFilters = requestURL.ANDFilters.split('|');
    }
    if (requestURL.ORFilters) {
        ORFilters = requestURL.ORFilters.split('|');
    }
    return {
        id : id,
        elasticURL: userRequestParams.elasticURL,
        query: m.prop(requestURL.query || (userRequestParams.query || '*')),
        userDefinedANDFilters: ANDFilters || [],
        userDefinedORFilters: ORFilters || [],
        dashboardDefinedANDFilters: userRequestParams.ANDFilters || [],
        dashboardDefinedORFilters: userRequestParams.ORFilters || [],
        preRequest: userRequestParams.preRequest,
        postRequest: userRequestParams.postRequest,
        aggregations : aggs || [],
        size: userRequestParams.size,
        page: userRequestParams.page,
        data: null,
        formattedData: {},
        complete: m.prop(false),
        sort: m.prop(requestURL.sort || userRequestParams.sort),
        sortMap: userRequestParams.sortMap
    };
};

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
                    dataReady ? m.component(params.widget.display.component, params) : params.vm.loadingIcon())
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
