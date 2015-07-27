'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('./utils');
var History = require('exports?History!history');

var searchDashboard = {};

searchDashboard.view = function (ctrl, params, children) {
    return [
        m('.row', !ctrl.vm.hidden ? [] : [
            m('.col-md-12',ctrl.drawWidgets(params))
            ])
        ];
};

//search widget state is in a vm
searchDashboard.controller = function (elasticSearchURL, query, widgets, nodeDisplay) {

    this.elasticPath = elasticSearchURL;
    this.widgets = widgets || [];
    this.hidden = m.prop(false);
    this.error = m.prop('');

    this.elastic = {};
    this.elastic.query =  query || m.prop(''); //query will be pushed from widgets? maybe
    this.elastic.optionalFilters = []; //filters will be pushed from widgets, init at zero
    this.elastic.requiredFilters = [];
    this.elastic.aggregations = []; //aggregations will be pushed from widgets, init at zero
    this.elastic.results = null;
    this.elastic.sort('Relevance');

    this.addWidget = function (widget) {
        this.widgets.push(widget);
    };

    this.search = function(){
        utils.search(this.elastic).then(this.updateWidgets.bind(this));
    };

    this.updateWidgets = function () { //push new aggregation data to widget, TODO only update if nessesary
        this.widgets.forEach(
            function (widget) {
                if (widget.name in Object.keys(this.elastic.results)) {
                    widget.parser(this.elastic.results[widget.name]);
                }
            }
        );
    };

    this.drawWidgets = function (params) { //TODO work out which is best...
        //returns grid of widgets
        return [m.component(this.widget[0], {}, params)];
    };
};

module.exports = searchDashboard;
