'use strict';
//Defines a template for a basic search widget
var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var utils = require('./utils');
var charts = require('charts');
var searchWidget = require('searchWidget');
var searchDashboard = require('searchDashboard');

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

profileDashboard.init = function() {
    this.dashboard = new searchDashboard.controller('URL', [], null);
    var contributers = new searchWidget.controller(
        'contributers',
        charts.donutChart,
        profileDashboard.contributersAgg(),
        charts.singleLevelAggParser,
        {'onclick': function (d) {utils.updateFilter(this.dashboard.elastic, 'match:shareProperties.source:' + d.name, true); }} //TODO check "this" usage
    );

    var contributersByTimes = new searchWidget.controller(
        'contributersByTimes',
        charts.timeseriesChart,
        profileDashboard.contributersByTimesAgg(),
        charts.twoLevelAggParser,
        null //no callbacks, this is purely for display
    );

    this.dashboard.addWidget(contributers);
    this.dashboard.addWidget(contributersByTimes);
    return this.dashboard;
};

module.exports = profileDashboard;
