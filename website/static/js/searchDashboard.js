'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var SearchWidgetPanel = require('js/searchWidget');
var History = require('exports?History!history');

var searchDashboard = {};

searchDashboard.view = function (ctrl, params, children) {
    return m('.col-lg-12', [] ,ctrl.hidden() ? [] : [ctrl.widgets.map(function(widget){
                return m.component(SearchWidgetPanel,{key : widget.name, widget: widget, vm: ctrl.vm});
            })]);
};

searchDashboard.vm = {};

searchDashboard.controller = function (params) {
    var self = this;
    //search dashboard state
    self.widgets = params.widgets || [];
    self.hidden = m.prop(false);
    self.error = m.prop('');

    //search model state
    self.vm = searchDashboard.vm;
    self.vm.elasticURL = params.elasticURL;
    self.vm.query =  params.query || m.prop('*'); //query will be pushed from widgets? maybe
    self.vm.optionalFilters = []; //filters will be pushed from widgets, init at zero
    self.vm.requiredFilters = [];
    self.vm.aggregations = [];
    self.vm.widgetsToUpdate = [];
    if (self.widgets){
        self.widgets.forEach(function(widget){
            self.vm.aggregations.push(widget.aggregation);
            self.vm.widgetsToUpdate.push(widget.levelNames[0]); //redraw all to start with
        });
    }
    self.vm.loadStats = true;
    self.vm.results = null; //unused, only for backwards compadibility with utils TODO remove
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
};


module.exports = searchDashboard;
