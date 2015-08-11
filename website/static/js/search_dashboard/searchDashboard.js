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
    self.vm.elasticURL = params.elasticURL;
    self.vm.pageTitle = params.pageTitle;
    self.vm.query =  params.query || m.prop('*');
    self.vm.optionalFilters = params.optionalFilters || [];
    self.vm.requiredFilters = params.requiredFilters || [];
    self.vm.aggregations = [];
    self.vm.widgetsToUpdate = [];
    self.vm.widgetIds = [];
    if (self.widgets){
        self.widgets.forEach(function(widget){
            self.vm.aggregations.push(widget.aggregation);
            self.vm.widgetIds.push(widget.id);
        });
    }
    self.vm.chartHandles = [];
    self.vm.rowHeights = {};
    self.vm.loadStats = true;
    self.vm.results = null; //unused, only for backwards compatibility with utils TODO remove
    self.vm.data = null;
    self.vm.dataLoaded = m.prop(false);

    self.vm.sort = m.prop($osf.urlParams().sort || 'Relevance');
    self.vm.resultsLoading = m.prop(false);
    self.vm.rawNormedLoaded = m.prop(false);
    self.vm.sortMap = {
        Date: 'providerUpdatedDateTime', //TODO should come in from profile
        Relevance: null
    };

    utils.search(self.vm); //initial search to init charts, redraw called inside utils, and will update widgets...

    History.Adapter.bind(window, 'statechange', function(e) {
        var historyChanged = utils.updateHistory(self.vm);
        if (historyChanged){ widgetUtils.signalWidgetsToUpdate(self.vm, self.vm.widgetIds);}
    });
};


module.exports = searchDashboard;
