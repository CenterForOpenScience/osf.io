'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var SearchWidget = require('js/searchWidget');
var History = require('exports?History!history');

var searchDashboard = {};

searchDashboard.view = function (ctrl, params, children) {
    return m('.row', [] ,ctrl.hidden() ? [] : [ctrl.widgets.map(function(widget){
                widget.dataLoaded = m.prop(true); //TODO hardcoded for now
                return m('.col',[],[m.component(SearchWidget,{key : widget.name, data: widget})]);
            })]);
};

searchDashboard.controller = function (params) {

    //search dashboard state
    this.widgets = params.widgets || [];
    this.hidden = m.prop(false);
    this.error = m.prop('');

    //search model state
    this.elastic = {};
    this.elastic.elasticPath = params.elasticUrl;
    this.elastic.query =  params.query || m.prop(''); //query will be pushed from widgets? maybe
    this.elastic.optionalFilters = []; //filters will be pushed from widgets, init at zero
    this.elastic.requiredFilters = [];
    this.elastic.aggregations = []; //aggregations will be pushed from widgets, init at zero
    this.elastic.results = null;
    this.elastic.dataLoaded = m.prop(true);
    //this.elastic.sort('Relevance');

    //this.addWidget = function (widget) {
    //    this.widgets.push(widget);
    //};
    //
    //this.search = function(){
    //    utils.search(this.elastic).then(this.updateWidgets.bind(this)); //TODO force redraw here
    //};
    //
    //this.updateWidgets = function () { //push new aggregation data to widget, TODO only update if nessesary
    //    this.widgets.forEach(
    //        function (widget) {
    //            if (widget.name in Object.keys(this.elastic.results)) {
    //                widget.parser(this.elastic.results[widget.name]);
    //            }
    //        }
    //    );
    //};
};

module.exports = searchDashboard;
