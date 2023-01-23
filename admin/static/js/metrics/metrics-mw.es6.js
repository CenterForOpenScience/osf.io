'use strict';

require('c3/c3.css');
require('keen-dataviz/dist/keen-dataviz.min.css');


var c3 = require('c3/c3.js');
var keen = require('keen-js');
var keenDataviz = require('keen-dataviz');
var keenAnalysis = require('keen-analysis');
var $ = require('jquery');

var client = new keenAnalysis({
    projectId: keenProjectId,
    readKey: keenReadKey
});

var publicClient = new keenAnalysis({
    projectId: keenPublicProjectId,
    readKey: keenPublicReadKey
});

// Heights and Colors for the below rendered
// Keen and c3 Data visualizations
var defaultHeight = 200;
var bigMetricHeight = 350;
var institutionTableHeight = "auto";

var defaultColor = '#00BBDE';
var monthColor = '#0CF5DB';
var yearColor = '#0CEB92';
var dayColor = '#0C93F5';
var privateColor = '#F20066';
var publicColor = '#FFD300';


function MetricParams(params) {
    this.params = params;

    // params
    //   eventCollection -- name of metrics api endpoint
    //   targetProperty -- property to extract in response
    //   timeframe -- <str> or <obj> with .start & .end keys
    //     <str> - previous_${count}_${period}
    //       $count -- int >= 1
    //       $period -- days, weeks, months
    //   timezone -- timezone (do we use this?)
    //   interval -- used by some respReformatters (interval for responses)
    //   groupBy -- <list> properties to group by ???
    //   respReformatter -- what type of response processor is this
    //     singleval
    //       targetProperty
    //     interval
    //       interval
    //       targetProperty
    //     extract-list
    //       listKey
    //       nameKey
    //       resultKey
    //     just-return
    //       *no properties*
    //     grouped-interval
    //       interval
    //       groupBy[0], groupBy[1]
    //       targetProperty
    //     table
    //       tableProperties
    //   listKey -- (used by extract-list) --- ???
    //   nameKey -- (used by extract-list) --- ???
    //   resultKey -- (used by extract-list) --- ???

    //   endpoint -- either "reports" or "query", defaults to "reports"

    //   filters -- used for NodeLogs & legacy download counts
    //     property_name
    //     operator
    //     property_value
    //     timezone
}

function makeMetricsUrl(newQuery) {
    var queryParams = {};

    if (newQuery.timeframe) {
        if (typeof newQuery.timeframe === 'object') {
            queryParams["timeframeStart"] = newQuery.timeframe.start;
            queryParams["timeframeEnd"] = newQuery.timeframe.end;
        }
        else {
            queryParams["timeframe"] = newQuery.timeframe;
        }
    }

    var urlRoot;
    if (newQuery.endpoint && newQuery.endpoint === 'query') {
        urlRoot = metricsUrl.replace('reports', 'query') + newQuery.eventCollection + '/';
    }
    else { // default to 'reports' endpoint
        urlRoot = metricsUrl + newQuery.eventCollection + '/recent/';
    }
    var newUrl = new URL(urlRoot);
    for (var key in queryParams) {
        if (queryParams.hasOwnProperty(key)) {
            newUrl.searchParams.append(key, queryParams[key]);
        }
    }

    return newUrl;
}

// take a property name like 'foo.bar' and a data structure and return data.foo.bar
function _diveIntoProperties(propertyName, data) {
    var propertydive = propertyName.split('.');
    var tmp = data;
    propertydive.forEach(property => {
        if (tmp !== undefined) {
            tmp = tmp[property];
        }
    });
    return tmp;
}


function _query2Promise(queryParams) {
    // Localize timezone if none is set
    if (!queryParams.timezone) {
        queryParams.timezone = new Date().getTimezoneOffset() * -60;
    }

    return $.get(makeMetricsUrl(queryParams));
}

/**
 * Take a list of MetricParams objects: call them, resolve them, turn them into outputs
 *
 * @method _resolveQueries
 * @param {Array} queries - Array of MetricParams objects to call and resolve.
 * @return {Array} array of response outputs
 * @return {Object} a single response output
 */
function _resolveQueries(queries) {

    var promises = [];
    queries.forEach(query => {
        promises.push(_query2Promise(query.params));
    });

    // if multiple promises, return array of outputs
    // if single promise, return output w/o array wrapper
    return promises.length > 1 ? Promise.all(promises) : promises[0];
}

/**
 * Take a MetricParams object and a metric api response and remap the response to a structure
 * suitable for passing to the `.chart()` method of a keenDataviz object.
 *
 * @method reformatResponse
 * @param {MetricParams} newQuery - MetricParams object representing a query to the metrics endpoint
 * @param {Object} res - response from metrics api endpoint
 * @return {Object} - remapped results data structure
 */
function reformatResponse(newQuery, res) {
    var keenFormatResp = {
        query: newQuery,
    };

    if (newQuery.respReformatter === "interval") {
        // take list of data and remap each to:
        //   {value: $targetProperty, timeframe: {start: $start, end: $end}}
        // currently assumes that both input and output are bucketed on daily intervals
        keenFormatResp['result'] = [];
        var interval = 1;
        if (newQuery.interval !== 'daily') {
            console.debug('ResponseReformatter: Unsupported interval in query:', newQuery);
        }

        res.data.forEach(entry => {
            var timestamp = entry['attributes']['report_date'];
            var remade = {
                timeframe: getInterval(timestamp, interval),
                value: entry['attributes'][newQuery.targetProperty],
            };
            keenFormatResp['result'].push(remade);
        });
    }
    else if (newQuery.respReformatter === "grouped-interval") {
        // take list of data and group by property by interval (currently only daily interval
        // is supported
        // newQuery.groupBy is a two-entry array
        //   groupBy[0] is the name of the group label in the output data
        //   groupBy[1] is the name of the group label in the input data (from res)
        //   targetProperty is the name of the property (must be dereferenced)
        var interval = 1;
        if (newQuery.interval !== "daily") {
            console.debug('ResponseReformatter: Unsupported interval in query:', newQuery);
        }

        var groupKeySrc = newQuery.groupBy[0];
        var groupKeyTgt = newQuery.groupBy[1];
        var intervals = {};
        res.data.forEach(entry => {
            var reportDate = entry.attributes.report_date;
            if (!intervals[reportDate]) {
                intervals[reportDate] = {
                    timeframe: getInterval(reportDate, interval),
                    value: [],
                };
            }
            intervals[reportDate].value.push({
                groupKeySrc: entry.attributes[groupKeyTgt],
                result: _diveIntoProperties(newQuery.targetProperty, entry.attributes),
            });
        });

        keenFormatResp['result'] = Object.values(intervals);
    }
    else if (newQuery.respReformatter === "singleval") {
        // output should be a single value in a key called "result"
        // input may be an object or a one-element array; unwrap array
        //   targetProperty is the name of the property in the unwrapped response
        var thisData = Array.isArray(res.data) ? res.data[0] : res.data;
        if (!thisData.attributes) {
            keenFormatResp['result'] = undefined;
        }
        else {
            keenFormatResp['result'] = _diveIntoProperties(newQuery.targetProperty, thisData.attributes);
        }
    }
    else if (newQuery.respReformatter === "table") {
        // turn input data into list of objects
        //  tableProperties is a whitelist of properties to transfer to the output list
        keenFormatResp['result'] = [];
        res.data.forEach(thisData => {
            var remade = {};
            newQuery.tableProperties.forEach(propName => {
                remade[propName] = _diveIntoProperties(propName, thisData.attributes);
            });
            keenFormatResp['result'].push(remade);
        });
    }
    else if (newQuery.respReformatter === "just-return") {
        keenFormatResp['result'] = [];
        res.data.forEach(thisData => {
            var attrs = thisData['attributes'];
            var interval = 1;
            var remade = {
                timeframe: getInterval(attrs.report_date, interval),
                attributes: attrs,
            };
            keenFormatResp['result'].push(remade);
        });
    }
    else if (newQuery.respReformatter === "extract-list") {
        // take a list of daily tallies and turn them into a different list
        // input data format (res.data): [
        //   {attributes: {report_date: "2022-12-03", $listKey: [
        //     {$nameKey: "foo", $resultKey: 3}, {$nameKey: "bar", $resultKey: 10}
        //   ]}},
        //   {attributes: {report_date: "2022-12-04", $listKey: [
        //     {$nameKey: "foo", $resultKey: 5}, {$nameKey: "bar", $resultKey: 12}
        //   ]}},
        // ]
        // output data format (keenFormatResp.result): [
        //   {timeframe: {start: $start, end: $end}, value: [
        //     {key: "foo", result: 3}, {key: "bar", result: 10}
        //   ]},
        //   {timeframe: {start: $start, end: $end}, value: [
        //     {key: "foo", result: 5}, {key: "bar", result: 12}
        //   ]},
        // ]
        keenFormatResp['result'] = [];
        var interval = 1;

        res.data.forEach(thisData => {
            var attrs = thisData['attributes'];
            var remade = {
                timeframe: getInterval(attrs.report_date, interval),
                value: [],
            };
            attrs[newQuery.listKey].forEach(entry => {
                remade.value.push({
                    key: entry[newQuery.nameKey],
                    result: _diveIntoProperties(newQuery.resultKey, entry),
                });
            });
            keenFormatResp['result'].push(remade);
        });
    }
    else {
        console.debug('ResponseReformatter: reformatter not supported?', newQuery.respReformatter);
    }

    return keenFormatResp;
}


/**
 * Configure a timeframe for the past day for a keen query
 * Can either be used to get a time frame for one day from today, or one day
 * starting from one month ago.
 *
 * @method getOneDayTimeframe
 * @param {Integer} daysBack - the number of days back to start the one day timeframe
 * @param {Integer} monthsBack - the number of months back to start the one day timeframe
 * @return {Object} the keen-formatted timeframe
 */
var getOneDayTimeframe = function(daysBack, monthsBack) {
    var start = null;
    var end = null;
    var today = new Date();

    today.setMonth(today.getMonth() - monthsBack);
    if (daysBack) {
        today.setUTCDate(today.getDate() - daysBack);
    } else {
        today.setUTCDate(1);
    }
    today.setUTCHours(0, 0, 0, 0, 0);
    start = today.toISOString();
    today.setDate(today.getDate() + 1);
    end = today.toISOString();
    return {
        "start": start.replace('T00:00:00.000Z', ''),
        "end": end.replace('T00:00:00.000Z', ''),
    };
};

/**
 * Configure a time frame for $endDaysBack days ago (end) and $totalDays days prior to that (start)
 *
 * @method getVariableDayTimeframe
 * @param {Integer} endDaysBack - the number of days back to set as the end day
 * @param {Integer} totalDays - the number of days before end day to reach the start day
 * @return {Object} the keen-formatted timeframe
 */
var getVariableDayTimeframe = function(endDaysBack, totalDays) {
    var start = null;
    var end = null;
    var date = new Date();

    date.setUTCDate(date.getDate() - endDaysBack);
    date.setUTCHours(0, 0, 0, 0, 0);

    end = date.toISOString();

    date.setDate(date.getDate() - totalDays);
    start = date.toISOString();
    return {
        "start": start.replace('T00:00:00.000Z', ''),
        "end": end.replace('T00:00:00.000Z', ''),
    };
};

/**
 * Configure a timeframe ending on endDate (end) and starting priorDays prior (start)
 *
 * @method getInterval
 * @param {str} endDate - the last day of the timeframe (dt format: mm-dd-yyyy)
 * @param {Integer} priorDays - the number of days back to reach the start day
 * @return {Object} the keen-formatted timeframe
 */
var getInterval = function(endDate, priorDays) {
    var start = null;
    var end = null;
    var date = new Date(endDate);

    date.setUTCDate(date.getDate());
    date.setUTCHours(0, 0, 0, 0, 0);

    end = date.toISOString();

    date.setDate(date.getDate() - priorDays);
    start = date.toISOString();
    return {
        "start": start.replace('T00:00:00.000Z', ''),
        "end": end.replace('T00:00:00.000Z', ''),
    };
};

/**
 * Configure a Title for a chart dealing with the past month or day
 *
 * @method getMonthTitle
 * @param {Object} metric - metric result object to get the date from
 * @return {String} the title for the monthly metric chart
 */
// KRA-NOTE - reach into metric here
var getMetricTitle = function(metric, type) {

    if (metric.params.timeframe.start) {

        var monthNames = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ];
        var date = null;
        var end = null;
        var title = null;

        if (type === "month") {
            date = new Date(metric.params.timeframe.start);
            title =  monthNames[date.getUTCMonth()] + " to " + monthNames[(date.getUTCMonth() + 1)%12];
        }
        else if (type === "day") {
            date = metric.params.timeframe.start.replace('T00:00:00.000Z', '');
            end = metric.params.timeframe.end.replace('T00:00:00.000Z', '');
            title =  date + " until " + end;
        }

    }
    else {
        title = metric.params.timeframe;
    }

    return title;
};

var renderKeenMetric = function(element, type, query, height, colors, keenClient) {

    if (!keenClient) {
        keenClient = client;
    }

    var chart = new keenDataviz()
        .el(element)
        .height(height)
        .title(' ')
        .type(type)
        .prepare();

    if (colors) {
        chart.colors([colors]);
    }

    keenClient
        .run(query)
        .then(function(res){
            var metricChart = chart.data(res);
            metricChart.dataset.sortRows("desc", function(row) {
                return row[1]
            });
            metricChart.render();
        })
        .catch(function(err){
            chart.message(err.message);
        });
};

var renderNodeLogsForOneUserChart = function(user_id) {
    var chart = new keenDataviz()
        .el('#yesterdays-node-logs-by-user')
        .height(bigMetricHeight)
        .title('Individual Logs for ' + '<a href=../users/' + user_id + '>' + user_id + '</a>')
        .type('line')
        .prepare();

    client
        .query('count', {
            event_collection: "node_log_events",
            interval: "hourly",
            group_by: "action",
            filters: [{
                property_name: 'user_id',
                operator: 'eq',
                property_value: user_id
            }],
            timeframe: "previous_1_days",
            timezone: "UTC"
        })
        .then(function(res){
            chart
                .data(res)
                .render();
        })
        .catch(function(err){
            chart.message(err.message);
        });
};

// called from pageview collection
var differenceGrowthBetweenMetrics = function(query1, query2, totalQuery, element, colors) {

    var percentOne;
    var percentTwo;

    var differenceMetric = new keenDataviz()
        .el(element)
        .chartType("metric")
        .chartOptions({
            suffix: '%'
        })
        .title(' ')
        .height(defaultHeight)
        .prepare();

    if (colors) {
        differenceMetric.colors([colors]);
    }

    _resolveQueries([
        query1,
        query2,
        totalQuery,
    ]).then(function(res) {
        var queryOneResult = reformatResponse(query1.params, res[0]).result;
        var queryTwoResult = reformatResponse(query2.params, res[1]).result;
        var totalResult    = reformatResponse(totalQuery.params, res[2]).result;

        percentOne = (queryOneResult/totalResult)*100;
        percentTwo = (queryTwoResult/totalResult)*100;

        var data = {
            "result": percentOne - percentTwo
        };

        differenceMetric.parseRawData(data).render();
    }).catch(function(err) {
        differenceMetric.message(err.message);
    });
};

var renderCalculationBetweenTwoQueries = function(query1, query2, element, differenceType,
                                                  calculationType, colors) {
    var result;
    var differenceMetric;

    if (calculationType === "percentage") {
        differenceMetric = new keenDataviz()
            .el(element)
            .type("metric")
            .title(' ')
            .height(defaultHeight)
            .chartOptions({
                suffix: '%'
            })
            .prepare();
    }
    else {
        differenceMetric = new keenDataviz()
            .el(element)
            .height(defaultHeight)
            .chartType("metric")
            .title(' ')
            .prepare();
    }

    if (colors) {
        differenceMetric.colors([colors]);
    }

    differenceMetric.title(getMetricTitle(query1, differenceType));

    _resolveQueries([
        query1,
        query2,
    ]).then(function(res) {
        var metricOneResult = reformatResponse(query1.params, res[0]).result;
        var metricTwoResult = reformatResponse(query2.params, res[1]).result;

        if (calculationType === "subtraction") {
            result = metricOneResult - metricTwoResult;
        }
        else if (calculationType === "percentage") {
            result = (metricOneResult/metricTwoResult) * 100;
        }
        else if (calculationType === "division") {
            result = metricOneResult/metricTwoResult;
        }

        var data = {
            "result": result
        };

        differenceMetric.parseRawData(data).render();
    })
    .catch(function(err){
        differenceMetric.message(err.message);
    });
};

var renderMetricsForInsts = function(instQuery, eachMetric) {
    _resolveQueries([instQuery]).then(res => {
        eachMetric.forEach(me => {
            var newParams = $.extend({tableProperties: ['institution_name',  me[1]]}, instQuery.params);
            var newRes = reformatResponse(newParams, res);
            var chart = new keenDataviz()
                .el(me[0])
                .height(institutionTableHeight)
                .title(' ')
                .type('table')
                .prepare();

            var metricChart = chart.data(newRes);
            metricChart.dataset.sortRows("desc", function(row) {
                return row[1];
            });
            metricChart.render();
        });
    }).fail(function (jqXHR, textStatus, err) {
        eachMetric.forEach(me => {
            var chart = new keenDataviz()
                .el(me[0])
                .height(institutionTableHeight)
                .title(' ')
                .type('table')
                .prepare();
            chart.message(err.message);
        });
    });
};

var renderMetric = function(element, type, query, height, colors) {

    var chart = new keenDataviz()
        .el(element)
        .height(height)
        .title(' ')
        .type(type)
        .prepare();

    if (colors) {
        chart.colors([colors]);
    }

    _resolveQueries([query]).then(res => {
        var newRes = reformatResponse(query.params, res);
        var metricChart = chart.data(newRes);
        metricChart.dataset.sortRows("desc", function(row) {
            return row[1];
        });
        metricChart.render();
    }).fail(function (jqXHR, textStatus, err) {
        chart.message(err.message);
    });
};


// Common Queries

// Active user count! - Total Confirmed Users of the OSF
var activeUsersQuery = new MetricParams({
    eventCollection: "user_summary",
    targetProperty: "active",
    timeframe: "previous_1_days",
    timezone: "UTC",
    respReformatter: "singleval",
});

var dailyActiveUsersQuery = new MetricParams({
    eventCollection: "unique_user_visits",
    targetProperty: "unique_visits.0.count",
    timeframe: "previous_1_days",
    timezone: "UTC",
    endpoint: "query",
    respReformatter: "singleval",
});

var totalProjectsQuery = new MetricParams({
    eventCollection: "node_summary",
    targetProperty: "projects.total",
    timezone: "UTC",
    timeframe: "previous_1_days",
    respReformatter: "singleval",
});


// <+><+><+><+><+><+
//    user data    |
// ><+><+><+><+><+>+

var renderMainCounts = function() {

    // Active user chart!
    var activeUserChartQuery = new MetricParams({
        eventCollection: "user_summary",
        interval: "daily",
        targetProperty: "active",
        timeframe: "previous_800_days",
        timezone: "UTC",
        respReformatter: "interval",
    });
    renderMetric("#active-user-chart", "line", activeUserChartQuery, bigMetricHeight);
    renderMetric("#active-user-count", "metric", activeUsersQuery, bigMetricHeight);

    // Daily Gain
    var yesterday_user_count = new MetricParams({
        eventCollection: "user_summary",
        targetProperty: "active",
        timeframe: getOneDayTimeframe(1, null),
        respReformatter: "singleval",
    });

    var two_days_ago_user_count = new MetricParams({
        eventCollection: "user_summary",
        targetProperty: "active",
        timeframe: getOneDayTimeframe(2, null),
        respReformatter: "singleval",
    });
    renderCalculationBetweenTwoQueries(yesterday_user_count, two_days_ago_user_count,
                                       "#daily-user-increase", 'day', 'subtraction');

    // Monthly Gain
    var last_month_user_count = new MetricParams({
        eventCollection: "user_summary",
        targetProperty: "active",
        timeframe: getOneDayTimeframe(null, 1),
        respReformatter: "singleval",
    });

    var two_months_ago_user_count = new MetricParams({
        eventCollection: "user_summary",
        targetProperty: "active",
        timeframe: getOneDayTimeframe(null, 2),
        respReformatter: "singleval",
    });
    renderCalculationBetweenTwoQueries(last_month_user_count, two_months_ago_user_count,
                                       "#monthly-user-increase", 'month', 'subtraction',
                                       monthColor);

    var week_ago_user_count = new MetricParams({
        eventCollection: "user_summary",
        targetProperty: "unconfirmed",
        timeframe: getOneDayTimeframe(7, null),
        respReformatter: "singleval",
    });

    // New Unconfirmed Users - # of unconfirmed users in the past 7 days
    var yesterday_unconfirmed_user_count = new MetricParams({
        eventCollection: "user_summary",
        targetProperty: "unconfirmed",
        timeframe: getOneDayTimeframe(1, null),
        respReformatter: "singleval",
    });
    renderCalculationBetweenTwoQueries(yesterday_unconfirmed_user_count, week_ago_user_count,
                                       "#unverified-new-users", 'week', 'subtraction');

};

//  Weekly User Gain metrics
var renderWeeklyUserGainMetrics = function () {

    var weeklyUserGain = new MetricParams({
        eventCollection: "user_summary",
        timeframe: "previous_7_days",
        timezone: "UTC",
        respReformatter: "just-return",
    });

    var avgUserGainChart = new keenDataviz()
        .el("#average-gain-metric")
        .type("metric")
        .height(defaultHeight)
        .title(' ')
        .prepare();

    var weeklyUserGainChart = new keenDataviz()
        .el("#user-gain-chart")
        .type("line")
        .title(' ')
        .prepare();

    var previousWeekOfUsersByStatusChart = new keenDataviz()
        .el("#previous-7-days-of-users-by-status")
        .height(defaultHeight)
        .type("line")
        .prepare();

    _resolveQueries([weeklyUserGain]).then(res => {
        var newRes = reformatResponse(weeklyUserGain.params, res);

        var avgDailyUserSum = 0;
        var weeklyData = [];
        var weekByStatusData = [];
        var resultLen = newRes.result.length;

        for (var j = 0; j < resultLen - 1; j++) {
            var thisThing = newRes.result[j];
            weekByStatusData[j] = {
                timeframe: thisThing["timeframe"],
                value: [
                    {category: "Active", result: thisThing.attributes.active},
                    {category: "Unconfirmed", result: thisThing.attributes.unconfirmed},
                    {category: "Merged", result: thisThing.attributes.merged},
                    {category: "Deactivated", result: thisThing.attributes.deactivated},
                ]
            };

            var nextThing = newRes.result[j + 1];
            if (nextThing) {
                avgDailyUserSum += (thisThing.attributes.active - nextThing.attributes.active);
                weeklyData.push({
                    value: thisThing.attributes.active - nextThing.attributes.active,
                    timeframe: thisThing.timeframe,
                });
            }
        }

        avgUserGainChart.parseRawData({result: avgDailyUserSum / (resultLen - 1)}).render();
        weeklyUserGainChart.parseRawData({result: weeklyData}).render();
        previousWeekOfUsersByStatusChart.parseRawData({result: weekByStatusData}).render();
    });
};

var renderEmailDomainsChart = function() {
    // Registrations by Email Domain
    var emailDomains = new MetricParams({
        eventCollection: "new_user_domains",
        groupBy: ["domain", "domain"],
        interval: "daily",
        timeframe: "previous_7_days",
        timezone: "UTC",
        respReformatter: "grouped-interval",
    });

    var chart = new keenDataviz()
        .el('#user-registration-by-email-domain')
        .title(' ')
        .type('line')
        .prepare();

    _resolveQueries([emailDomains]).then(res => {
        var newRes = reformatResponse(emailDomains.params, res);
        var chartWithData = chart.data(newRes);
        chartWithData.dataset.filterColumns(function (column, index) {
            var emailThreshhold = 1;
            for (var i = 0; i < column.length; i++) {
                if (column[i] > emailThreshhold) {
                    return column;
                }
            }
        });
        chartWithData.render();
    }).fail(function (jqXHR, textStatus, err) {
        chart.message(err.message);
    });
};

var NodeLogsPerUser = function() {
    var chart = new keenDataviz()
        .el('#yesterdays-node-logs-by-user')
        .title(' ')
        .height(bigMetricHeight)
        .chartOptions({
            data: {
                onclick: function (d, element) {
                    renderNodeLogsForOneUserChart(d.name);
                }
            }
        })

        .type('line')
        .prepare();

    client
        .query('count', {
            event_collection: 'node_log_events',
            group_by: "user_id",
            timeframe: 'previous_1_days',
            interval: 'hourly'
        })
        .then(function (res) {
            var chartWithData = chart.data(res);
            chartWithData.dataset.filterColumns(function (column, index) {
                var logThreshhold = 25;
                for (var i = 0; i < column.length; i++) {
                    if (column[i] > logThreshhold && column[0] != 'null' && column[0] != 'uj57r') {
                        return column;
                    }
                }
            });

            chartWithData.render();
        })
        .catch(function (err) {
            chart.message(err.message);
        });
};

var renderRawNodeMetrics = function() {
    var propertiesAndElements = [
        ['projects.public',               '#public-projects',              ],
        ['projects.private',              '#private-projects',             ],
        ['nodes.total',                   '#total-nodes',                  ],
        ['nodes.public',                  '#public-nodes',                 ],
        ['nodes.private',                 '#private-nodes',                ],
        ['registered_projects.total',     '#total-registered-projects',    ],
        ['registered_projects.public',    '#public-registered-projects',   ],
        ['registered_projects.embargoed', '#embargoed-registered-projects',],
        ['registered_nodes.total',        '#total-registered-nodes',       ],
        ['registered_nodes.public',       '#public-registered-nodes',      ],
        ['registered_nodes.embargoed',    '#embargoed-registered-nodes',   ],
    ];

    var piePropertiesAndElements = [
        ['#total-nodes-pie',               ['nodes.public', 'nodes.private'],                              ],
        ['#total-projects-pie',            ['projects.public', 'projects.private'],                        ],
        ['#total-registered-nodes-pie',    ['registered_nodes.public', 'registered_nodes.embargoed'],      ],
        ['#total-registered-projects-pie', ['registered_projects.public', 'registered_projects.embargoed'],],
    ];

    var nodeSummary = new MetricParams({
        eventCollection: "node_summary",
        timeframe: "previous_1_days",
        timezone: "UTC",
        respReformatter: "just-return",
    });

    var results = {};
    _resolveQueries([nodeSummary]).then(res => {
        var newRes = reformatResponse(nodeSummary.params, res);
        var attrs = newRes.result[0].attributes;

        propertiesAndElements.forEach(propAndEl => {
            var property = propAndEl[0];
            var element = propAndEl[1];

            var chart = new keenDataviz()
                .el(element)
                .height(defaultHeight)
                .title(' ')
                .type('metric')
                .prepare();

            if (property.includes('public')) {
                chart.colors([publicColor]);
            }
            else if (property.includes('private') || property.includes('embargoed')) {
                chart.colors([privateColor]);
            }

            var finalProp = _diveIntoProperties(property, attrs);
            chart.data({result: finalProp}).render();
            results[property] = finalProp;
        });

        piePropertiesAndElements.forEach(piePropAndEl => {
            var element = piePropAndEl[0];
            var properties = piePropAndEl[1];

            var publicData = properties[0];
            var privateData = properties[1];

            c3.generate({
                bindto: element,
                size: {height: defaultHeight*2},
                data: {
                    columns: [
                        ['public', results[publicData]],
                        ['private', results[privateData]],
                    ],
                    colors: {
                        public: publicColor,
                        private: privateColor
                    },
                    type : 'pie',
                }
            });
        });
    });
};


var UserGainMetrics = function() {
    renderMainCounts();
    renderWeeklyUserGainMetrics();
    renderEmailDomainsChart();
    NodeLogsPerUser();
};


// <+><+><+><+><+><+><+<+>+
//   institution metrics  |
// ><+><+><+><+><+><+><+><+

var InstitutionMetrics = function() {

    // Institutional Users over past 100 Days
    var institutional_user_chart = new MetricParams({
        eventCollection: "institution_summary",
        interval: "daily",
        targetProperty: "users.total",
        groupBy: ["institution.name", "institution_name"],
        timeframe: "previous_100_days",
        timezone: "UTC",
        respReformatter: "grouped-interval",
    });
    renderMetric("#institution-growth", "line", institutional_user_chart, 400);

    // Total Institutional Users
    var institutional_user_count = new MetricParams({
        eventCollection: "institution_summary",
        targetProperty: "users.total",
        timeframe: "previous_1_day",
        timezone: "UTC",
        respReformatter: "singleval",
    });
    renderMetric("#total-institutional-users", "metric", institutional_user_count, defaultHeight);

    // Total Instutional Users / Total OSF Users
    renderCalculationBetweenTwoQueries(institutional_user_count, activeUsersQuery,
                                       "#percentage-institutional-users", null, 'percentage');

    // Insitutional Nodes!
    var yesterdaysInstUserCount = new MetricParams({
        eventCollection: "institution_summary",
        timeframe: "previous_1_day",
        timezone: "UTC",
        respReformatter: "table",
    });
    renderMetricsForInsts(yesterdaysInstUserCount, [
        ["#affiliated-public-nodes",                  "users.total",                     ],
        ["#affiliated-private-nodes",                 "nodes.private",                   ],
        ["#affiliated-public-registered-nodes",       "registered_nodes.public",         ],
        ["#affiliated-embargoed-registered-nodes",    "registered_nodes.embargoed_v2",   ],
        ["#affiliated-public-projects",               "projects.public",                 ],
        ["#affiliated-private-projects",              "projects.private",                ],
        ["#affiliated-public-registered-projects",    "registered_projects.public",      ],
        ["#affiliated-embargoed-registered-projects", "registered_projects.embargoed_v2",],
    ]);
};


// <+><+><+><+><+><+><+<+>+
//   active user metrics |
// ><+><+><+><+><+><+><+><+

var ActiveUserMetrics = function() {

    // Recent Daily Unique Sessions
    var recentDailyUniqueSessions = new MetricParams({
        eventCollection: "user_visits",
        targetProperty: "unique_visits.0.count",
        interval: "daily",
        timeframe: "previous_14_days",
        timezone: "UTC",
        endpoint: "query",
        respReformatter: "singleval",
    });
    renderMetric("#recent-daily-unique-sessions", "line", recentDailyUniqueSessions, defaultHeight);

    // Daily Active Users
    renderMetric("#daily-active-users", "metric", dailyActiveUsersQuery, defaultHeight);

    // Daily Active Users / Total Users
    renderCalculationBetweenTwoQueries(dailyActiveUsersQuery, activeUsersQuery,
                                       "#daily-active-over-total-users", null, "percentage");

    // Monthly Active Users
    var monthlyActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: "previous_1_months",
        timezone: "UTC",
        endpoint: "query",
        respReformatter: "singleval",
    });
    renderMetric("#monthly-active-users", "metric", monthlyActiveUsersQuery, defaultHeight, monthColor);


    // Monthly Active Users / Total Users
    renderCalculationBetweenTwoQueries(monthlyActiveUsersQuery, activeUsersQuery,
                                       "#monthly-active-over-total-users", null, 'percentage', monthColor);


    // Monthly Growth of MAU% -- Two months ago vs 1 month ago
    var twoMonthsAgoActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: "previous_2_months",
        timezone: "UTC",
        endpoint: "query",
        respReformatter: "singleval",
    });
    differenceGrowthBetweenMetrics(twoMonthsAgoActiveUsersQuery, monthlyActiveUsersQuery,
                                   activeUsersQuery, "#monthly-active-user-increase", monthColor);

    // Yearly Active Users
    var yearlyActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: "previous_1_years",
        timezone: "UTC",
        endpoint: "query",
        respReformatter: "singleval",
    });
    renderMetric("#yearly-active-users", "metric", yearlyActiveUsersQuery, defaultHeight, yearColor);

    // Yearly Active Users / Total Users
    renderCalculationBetweenTwoQueries(yearlyActiveUsersQuery, activeUsersQuery,
                                       "#yearly-active-over-total-users", null, 'percentage', yearColor);

    // Average Projects per User
    renderCalculationBetweenTwoQueries(totalProjectsQuery, activeUsersQuery,
                                       "#projects-per-user", null, 'division');

    // Average Projects per MAU
    renderCalculationBetweenTwoQueries(totalProjectsQuery, monthlyActiveUsersQuery,
                                       "#projects-per-monthly-user", null, 'division');
};


// <+><+><+><+><+><+><+<+>+
//   healthy user metrics |
// ><+><+><+><+><+><+><+><+

var HealthyUserMetrics = function() {

    // Previous 30 Days Active Users
    var thirtyDaysActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: "previous_30_days",
        timezone: "UTC",
        endpoint: "query",
        respReformatter: "singleval",
    });

    // stickiness ratio - DAU/MAU
    renderCalculationBetweenTwoQueries(dailyActiveUsersQuery, thirtyDaysActiveUsersQuery,
                                       "#stickiness-ratio-1-day-ago", null, "percentage");

    // 7 Days back Active Users
    var weekBackThirtyDaysActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: getVariableDayTimeframe(7, 30),
        endpoint: "query",
        respReformatter: "singleval",
    });

    // 7 Days back Active Users
    var weekBackDailyActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: getVariableDayTimeframe(7, 1),
        endpoint: "query",
        respReformatter: "singleval",
    });

    // stickiness ratio - DAU/MAU for 1 week ago
    renderCalculationBetweenTwoQueries(weekBackDailyActiveUsersQuery, weekBackThirtyDaysActiveUsersQuery,
                                       "#stickiness-ratio-1-week-ago", null, "percentage");

    // 28 Days back Active Users
    var monthBackThirtyDaysActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: getVariableDayTimeframe(28, 30),
        endpoint: "query",
        respReformatter: "singleval",
    });

    // 28 Days back Active Users
    var monthBackDailyActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: getVariableDayTimeframe(28, 1),
        endpoint: "query",
        respReformatter: "singleval",
    });

    // stickiness ratio - DAU/MAU for 4 weeks ago
    renderCalculationBetweenTwoQueries(monthBackDailyActiveUsersQuery, monthBackThirtyDaysActiveUsersQuery,
                                       "#stickiness-ratio-4-weeks-ago", null, "percentage");

    // 364 Days back Active Users
    var yearBackThirtyDaysActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: getVariableDayTimeframe(364, 30),
        endpoint: "query",
        respReformatter: "singleval",
    });

    // 364 Days back Active Users
    var yearBackDailyActiveUsersQuery = new MetricParams({
        eventCollection: "unique_user_visits",
        targetProperty: "unique_visits.0.count",
        timeframe: getVariableDayTimeframe(364, 1),
        endpoint: "query",
        respReformatter: "singleval",
    });

    // stickiness ratio - DAU/MAU for 52 weeks ago
    renderCalculationBetweenTwoQueries(yearBackDailyActiveUsersQuery, yearBackThirtyDaysActiveUsersQuery,
                                       "#stickiness-ratio-52-weeks-ago", null, "percentage");
};


// <+><+><+><+><+>>+
//   raw numbers   |
// ><+><+><+><><+><+

var RawNumberMetrics = function() {
    renderMetric("#total-projects", "metric", totalProjectsQuery, defaultHeight);
    renderRawNodeMetrics();
};


// <+><+><+><><>+
//     addons   |
// ><+><+><+<+><+

var AddonMetrics = function() {
    // Previous 7 days of linked addon by addon name
    var linked_addon = new MetricParams({
        eventCollection: "storage_addon_usage",
        interval: "daily",
        timeframe: "previous_8_days",
        timezone: "UTC",
        listKey: "usage_by_addon",
        nameKey: "addon_shortname",
        resultKey: "linked_usersettings.total",
        respReformatter: "extract-list"
    });
    renderMetric('#previous-7-days-of-linked-addon-by-addon-name', "line", linked_addon, defaultHeight);
};


// <+><+><+><><>+
//   preprints   |
// ><+><+><+<+><+

var PreprintMetrics = function() {
    renderPreprintMetrics();
};

function renderPreprintMetrics(timeframe) {
    if (timeframe === undefined) {
        timeframe = "previous_30_days";
    }

    var preprint_created = new MetricParams({
        eventCollection: "preprint_summary",
        targetProperty: "preprint_count",
        groupBy: ["provider.name", "provider_key"],
        interval: "daily",
        timeframe: timeframe,
        timezone: "UTC",
        respReformatter: "grouped-interval",
    });

    renderMetric("#preprints-added", "line", preprint_created, defaultHeight);
}


// <+><+><+><><>+
//   file download counts   |
// ><+><+><+<+><+

var DownloadMetrics = function() {

    // ********** legacy keen **********
    var totalDownloadsQuery = new keenAnalysis.Query("count", {
        eventCollection: "file_stats",
        timeframe: 'previous_1_days',
        filters: [{
            property_name: 'action.type',
            operator: 'eq',
            property_value: 'download_file',
            timezone: "UTC"
        }]
    });
    renderKeenMetric("#number-of-downloads", "metric", totalDownloadsQuery,
                     defaultHeight, defaultColor, publicClient);

    // ********** legacy keen **********
    var uniqueDownloadsQuery = new keenAnalysis.Query("count_unique", {
        eventCollection: "file_stats",
        timeframe: 'previous_1_days',
        target_property: 'file.resource',
        filters: [{
            property_name: 'action.type',
            operator: 'eq',
            property_value: 'download_file',
            timezone: "UTC"
        }]
    });
    renderKeenMetric("#number-of-unique-downloads", "metric", uniqueDownloadsQuery,
                     defaultHeight, defaultColor, publicClient);

    renderDownloadMetrics();
};

function renderDownloadMetrics(timeframe) {
    if (timeframe === undefined) {
        timeframe = "previous_30_days";
    }

    var downloadCount = new MetricParams({
        eventCollection: "download_count",
        interval: "daily",
        targetProperty: "daily_file_downloads",
        timeframe: timeframe,
        timezone: "UTC",
        respReformatter: "interval",
    });
    renderMetric("#download-counts", "line", downloadCount, defaultHeight);
}




module.exports = {
    UserGainMetrics: UserGainMetrics,
    NodeLogsPerUser: NodeLogsPerUser,
    InstitutionMetrics: InstitutionMetrics,
    ActiveUserMetrics: ActiveUserMetrics,
    HealthyUserMetrics:HealthyUserMetrics,
    RawNumberMetrics: RawNumberMetrics,
    AddonMetrics: AddonMetrics,
    PreprintMetrics: PreprintMetrics,
    DownloadMetrics: DownloadMetrics,
    KeenRenderMetrics: renderKeenMetric,
    RenderPreprintMetrics: renderPreprintMetrics,
    RenderDownloadMetrics: renderDownloadMetrics,
};
