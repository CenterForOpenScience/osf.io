'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var widgetUtils = require('js/search_dashboard/widgetUtils');
var charts = require('js/search_dashboard/charts');
var ResultsWidget = require('js/search_dashboard/resultsWidget');
var searchDashboard = require('js/search_dashboard/searchDashboard');

var profileDashboard = {};

/**
 * Setups elastic aggregations to get contributers.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.contributersAgg = function(){
    return {'sources': utils.termsFilter('field', '_type')};
};

/**
 * Setups elastic aggregations to get contributers by time data.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.contributersByTimesAgg = function() {
    var dateTemp = new Date(); //get current time
    dateTemp.setMonth(dateTemp.getMonth() - 3);
    var threeMonthsAgo = dateTemp.getTime();
    var agg = {'sourcesByTimes': utils.termsFilter('field', '_type')};
    agg.sourcesByTimes.aggregations = {'sources' :
        utils.dateHistogramFilter('providerUpdatedDateTime', threeMonthsAgo)};
    return agg;
};

/**
* View function for the profile dashboard
*
* @param {Object} controller Object automatically passed in by mithril
* @return {m.component object}  initialised searchDashboard component
*/
profileDashboard.view = function(ctrl, params, children){
   return m.component(searchDashboard, {elasticURL: '/api/v1/share/search/', widgets : ctrl.widgets, rows: 2});
};

/**
 * controller function for the ProfileDashboard. Basically a constructor that sets up a SearchDashboard.
 * Contains settings for all widgets. Contains Elastic Data.
 *
 * @return {m.component.controller}  returns itself
 */
profileDashboard.controller = function(params) {
    this.user = params.user;

    var userFilter = {}

    var contributers = {
        title: 'Contributers',
        size: ['.col-md-3', 260],
        row: 1,
        levelNames: ['sources'],
        display: charts.donutChart,
        aggregation: profileDashboard.contributersAgg(),
        callback: {'onclick': function (d) {
            utils.updateFilter(this.vm, 'match:shareProperties.source:' + d.name, true);
            widgetUtils.signalWidgetsToUpdate(this.vm,this.widget.thisWidgetUpdates);
        }},
        thisWidgetUpdates: ['sources', 'sourcesByTimes', 'results']
    };

    var contributersByTimes = {
        title: 'Contributers over time',
        size: ['.col-md-9', 260],
        row: 1,
        levelNames: ['sourcesByTimes','sources'],
        display: charts.timeseriesChart,
        aggregation: profileDashboard.contributersByTimesAgg(),
        callback: null, //no callbacks, this is purely for display
        thisWidgetUpdates: ['sources', 'sourcesByTimes', 'results']
    };

    var results = {
        title: 'Projects and Components',
        size: ['.col-md-12'],
        row: 2,
        levelNames: ['results'],
        display: ResultsWidget.display,
        aggregation: null, //this displays no stats, so needs no aggregations
        callback: null, //callbacks are all prebuilt into this widget
        thisWidgetUpdates: ['sources', 'sourcesByTimes', 'results']
    };

    this.widgets = [contributers, contributersByTimes, results];
};

module.exports = profileDashboard;
