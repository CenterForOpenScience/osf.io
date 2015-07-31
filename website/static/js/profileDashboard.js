'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var charts = require('js/charts');
var ResultsWidget = require('js/resultsWidget');
var searchDashboard = require('js/searchDashboard');

var profileDashboard = {};

profileDashboard.contributersAgg = function(){
    return {'sources': utils.termsFilter('field', '_type')};
};

profileDashboard.contributersByTimesAgg = function() {
    var dateTemp = new Date(); //get current time
    dateTemp.setMonth(dateTemp.getMonth() - 3);
    var threeMonthsAgo = dateTemp.getTime();
    var agg = {'sourcesByTimes': utils.termsFilter('field', '_type')};
    agg.sourcesByTimes.aggregations = {'sources' :
        utils.dateHistogramFilter('providerUpdatedDateTime', threeMonthsAgo)};
    return agg;
};

//sets up the profile dashboard, then returns set up searchDashboard object
profileDashboard.controller = function(params) {

    var contributers = {
        title: 'Your contributers',
        size: ['.col-md-3'],
        levelNames: ['sources'],
        display: charts.donutChart,
        aggregation: profileDashboard.contributersAgg(),
        callback: {'onclick': function (d) {
            utils.updateFilter(this.vm, 'match:shareProperties.source:' + d.name, true);
            utils.signalWidgetsToUpdate(this.vm,this.widget.thisWidgetUpdates);
        }},
        thisWidgetUpdates: ['sources', 'sourcesByTimes', 'results']
    };

    var contributersByTimes = {
        title: 'Your contributers over time',
        size: ['.col-md-9'],
        levelNames: ['sourcesByTimes','sources'],
        display: charts.timeseriesChart,
        aggregation: profileDashboard.contributersByTimesAgg(),
        callback: null, //no callbacks, this is purely for display
        thisWidgetUpdates: ['sources', 'sourcesByTimes', 'results']
    };

    var results = {
        title: 'Projects and Components',
        size: ['.col-md-12'],
        levelNames: ['results'],
        display: ResultsWidget.display,
        aggregation: null, //this displays no stats, so needs no aggregations
        callback: null, //callbacks are all prebuilt into this widget
        thisWidgetUpdates: ['sources', 'sourcesByTimes', 'results']
    };

    this.widgets = [contributers, contributersByTimes, results];
};

profileDashboard.view = function(ctrl, params, children){
   return m('.row', [], [m.component(searchDashboard, {elasticURL: '/api/v1/share/search/', widgets : ctrl.widgets})]);
};

module.exports = profileDashboard;
