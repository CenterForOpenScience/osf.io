'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('js/share/utils');
var charts = require('js/charts');
var searchWidget = require('js/searchWidget');
var searchDashboard = require('js/searchDashboard');

var profileDashboard = {};

profileDashboard.contributersAgg = function(){
    var sourcesQuery = {'match_all': {} };
    var sourcesAgg = {'contributers': utils.termsFilter('field', '_type')};
    return {'query' : sourcesQuery, 'aggregations': sourcesAgg, 'filters' : {}};
};

profileDashboard.contributersByTimesAgg = function() {
    var dateTemp = new Date(); //get current time
    dateTemp.setMonth(dateTemp.getMonth() - 3);
    var threeMonthsAgo = dateTemp.getTime();
    var dateHistogramQuery = {'match_all': {} };
    var dateHistogramAgg = {'contributersByTimes': utils.termsFilter('field', '_type')};
    dateHistogramAgg.contributersByTimes.aggregations = {'projectsOverTime' :
        utils.dateHistogramFilter('providerUpdatedDateTime', threeMonthsAgo)};
    return {'query' : dateHistogramQuery, 'aggregations': dateHistogramAgg, 'filters' : {} };
};

//sets up the profile dashboard, then returns set up searchDashboard object
profileDashboard.controller = function() {
    //this.dashboard = new searchDashboard.controller('URL', [], null);
    //var contributers = new searchWidget.controller(
    //    'contributers',
    //    charts.donutChart,
    //    profileDashboard.contributersAgg(),
    //    charts.singleLevelAggParser,
    //    null//{'onclick': function (d) {utils.updateFilter(this.dashboard.elastic, 'match:shareProperties.source:' + d.name, true); }} //TODO check "this" usage
    //);
    //
    //var contributersByTimes = new searchWidget.controller(
    //    'contributersByTimes',
    //    charts.timeseriesChart,
    //    profileDashboard.contributersByTimesAgg(),
    //    charts.twoLevelAggParser,
    //    null //no callbacks, this is purely for display
    //);

    var levelsA = ['contributers'];
    var contributers = {
        title: 'Your contributers',
        levelNames: levelsA,
        chart: charts.donutChart,
        agg: profileDashboard.contributersAgg(),
        parser: charts.singleLevelAggParser,
        callback: null//{'onclick': function (d) {utils.updateFilter(this.dashboard.elastic, 'match:shareProperties.source:' + d.name, true); }} //TODO check "this" usage
    };

    var levelsB = ['contributersByTimes','contributers'];
    var contributersByTimes = {
        title: 'Your contributers over time',
        levelNames: levelsB,
        chart: charts.timeseriesChart,
        agg: profileDashboard.contributersByTimesAgg(),
        parser: charts.twoLevelAggParser,
        callback: null //no callbacks, this is purely for display
    };

    //this.widgets = [contributers];
    this.widgets = [contributers, contributersByTimes];
    //this.dashboard.addWidget(contributers);
    //this.dashboard.addWidget(contributersByTimes);
    //return this.dashboard; //After return, view and controller functions of this object, will be that of the initialised searchDashboard object
};

profileDashboard.view = function(ctrl, params, children){
    //return m("a", {href: "http://google.com"}, "google"); //yields <a href="http://google.com">Google</a>
    return m('.row', [], [m.component(searchDashboard, {elasticUrl: '/api/v1/share/search/', widgets : ctrl.widgets})]);
};

module.exports = profileDashboard;
