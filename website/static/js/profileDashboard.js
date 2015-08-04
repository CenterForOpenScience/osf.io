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

var ctx = window.contextVars;
/**
 * Setups elastic aggregations to get contributers.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.contributorsAgg = function(){
    var agg = {'contributors': utils.termsFilter('field', 'contributors.url')};
    //agg.contributors.aggregations = {'contributorsName' :
    //    utils.termsFilter('field','contributors.fullname')};
    return agg;
};

/**
 * Setups elastic aggregations to get contributers by time data.
 *
 * @return {object} JSON elastic search aggregation
 */
profileDashboard.contributorsByTimesAgg = function() {
    var dateTemp = new Date(); //get current time
    dateTemp.setMonth(dateTemp.getMonth() - 3);
    var threeMonthsAgo = dateTemp.getTime();
    var agg = {'ContributorsByTimes': utils.termsFilter('field', 'projects.properties.contributors.fullname')};
    agg.ContributorsByTimes.aggregations = {'contributors' :
        utils.dateHistogramFilter('date_created', threeMonthsAgo)};
    return agg;
};

/**
* View function for the profile dashboard
*
* @param {Object} ctrl: controller Object automatically passed in by mithril
* @return {m.component object}  initialised searchDashboard component
*/
profileDashboard.view = function(ctrl) {
    return m.component(searchDashboard, ctrl.searchSetup);
};

/**
 * controller function for the ProfileDashboard. Basically a constructor that sets up a SearchDashboard.
 * Contains settings for all widgets. Contains Elastic Data.
 *
 * @return {m.component.controller} returns itself
 */
profileDashboard.controller = function(params) {
    var contributors = {
        title: 'Contributors',
        size: ['.col-md-3', 260],
        row: 1,
        levelNames: ['contributors','contributorsName'],
        display: charts.donutChart,
        displayArgs: {
            callback: { onclick : function (key) {
                utils.updateFilter(this.vm, 'match:contributors.url:' + key.name, true);
                widgetUtils.signalWidgetsToUpdate(this.vm, this.widget.thisWidgetUpdates);
            }},
        },
        aggregation: profileDashboard.contributorsAgg(),
        thisWidgetUpdates: ['Contributors', 'ContributorsByTimes', 'results'] //TODO give simple 'all' option
    };

    var contributorsByTimes = {
        title: 'Contributors over time',
        size: ['.col-md-9', 260],
        row: 1,
        levelNames: ['contributorsByTimes','sources'],
        display: charts.timeseriesChart,
        displayArgs: {},
        aggregation: profileDashboard.contributorsByTimesAgg(),
        thisWidgetUpdates: ['Contributors', 'ContributorsByTimes', 'results']
    };

    var results = {
        title: 'Projects and Components',
        size: ['.col-md-12'],
        row: 2,
        levelNames: ['results'],
        display: ResultsWidget.display,
        displayArgs: {},
        aggregation: null, //this displays no stats, so needs no aggregations
        thisWidgetUpdates: ['Contributors', 'ContributorsByTimes', 'results']
    };

    this.searchSetup = {
        elasticURL: '/api/v1/search/',
        user: ctx.user,
        widgets : [contributors, results],
        rows:2,
        requiredFilters: ['match:contributors.url:' + ctx.user]
    };
};

module.exports = profileDashboard;
