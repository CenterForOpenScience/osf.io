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
    var levelsA = ['sources'];
    var contributers = {
        title: 'Your contributers',
        levelNames: levelsA,
        chart: charts.donutChart,
        aggregation: profileDashboard.contributersAgg(),
        parser: charts.singleLevelAggParser,
        callback: {'onclick': function (d) {utils.updateFilter(this, 'match:shareProperties.source:' + d.name, true); }} //TODO check "this" usage
    };

    var levelsB = ['sourcesByTimes','sources'];
    var contributersByTimes = {
        title: 'Your contributers over time',
        levelNames: levelsB,
        chart: charts.timeseriesChart,
        aggregation: profileDashboard.contributersByTimesAgg(),
        parser: charts.twoLevelAggParser,
        callback: null //no callbacks, this is purely for display
    };

    this.widgets = [contributers, contributersByTimes];
};

profileDashboard.view = function(ctrl, params, children){
   return m('.row', [], [m.component(searchDashboard, {elasticURL: '/api/v1/share/search/', widgets : ctrl.widgets})]);
};

module.exports = profileDashboard;
