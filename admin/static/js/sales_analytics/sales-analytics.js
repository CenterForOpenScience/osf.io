'use strict';

var keen = require('keen-js');
var ss = require('simple-statistics');

keen.ready(runSalesAnalytics());

function runSalesAnalytics() {

    //  setup keen client
    var keenClient = new keen({
        projectId: keenProjectId,
        readKey : keenReadKey
    });

    //  keen query filters
    var nullUserFilter = {
        property_name: 'user.id',
        operator: 'ne',
        property_value: 'null'
    };
    var inactiveUserFilter = {
        property_name: 'user.id',
        operator: 'ne',
        property_value: ''
    };

    //  query for average user session length
    var userSessionQuery = new keen.Query('select_unique', {
        event_collection: 'pageviews',
        timeframe: 'previous_7_days',
        target_property: 'keen.timestamp',
        group_by: ['user.id', 'sessionId'],
        filters: [nullUserFilter]
    });

    //  query for average MAU (monthly active user) session length
    var activeUserSessionQuery = new keen.Query('select_unique', {
        event_collection: 'pageviews',
        timeframe: 'previous_7_days',
        target_property: 'keen.timestamp',
        group_by: ['user.id', 'sessionId'],
        filters: [nullUserFilter, inactiveUserFilter]
    });

    //  make query, process the result and visualize it
    var query = [userSessionQuery, activeUserSessionQuery];
    var chartAverageSessionUser = new keen.Dataviz();
    chartAverageSessionUser.el(document.getElementById('keen-chart-average-session-user')).prepare();
    var chartAverageSessionMAU = new keen.Dataviz();
    chartAverageSessionMAU.el(document.getElementById('keen-chart-average-session-mau')).prepare();

    var req = keenClient.run(query, function(err, res) {
        if (err) {
            console.log('keen query error: ' + err);
        }
        else {
            var dataSetUser = extractDataSet(res[0]);
            var dataSetMAU = extractDataSet(res[1]);
            var result1 = ss.mean(dataSetUser);
            var result2 = ss.mean(dataSetMAU);
            console.log('average user session length is ' + result1 + " ms" );
            console.log('average user session length (mau) is ' + result2 + " ms" );

            chartAverageSessionUser.attributes({ title: 'Average User Session Length in Minutes', width: 600 });
            chartAverageSessionUser.adapter({chartType: 'metric'});
            chartAverageSessionMAU.attributes({ title: 'Average MAU Session Length in Minutes', width: 600 });
            chartAverageSessionUser.parseRawData({result: result1/1000/60});
            chartAverageSessionMAU.parseRawData({result: result2/1000/60});
            chartAverageSessionUser.render();
            chartAverageSessionMAU.render();
        }
    });

    //  refresh every 10 minutes (testing)
    setInterval(function() {
        console.log('chart refresh');
        req.refresh();
    }, 1000 * 60 * 10);

    //  average user/mau session length each month for the past 12 months
    //var date = new Date();
    //var yearEnd = date.getFullYear();
    //var monthEnd = date.getMonth();
    //
    //var count = 12;
    //while (count-- > 0) {
    //    var yearStart = yearEnd - 1 < 0 ? yearEnd - 1 : yearEnd;
    //    var monthStart = (monthEnd - 1) % 12;
    //
    //    var dateStart = new Date(yearStart, monthStart, 1);
    //    var dateEnd = new Date(yearEnd, monthEnd, 1);
    //
    //    console.log(dateStart.toISOString());
    //    console.log(dateEnd.toISOString());
    //
    //    var userSessionQueryHistory = new keen.Query('select_unique', {
    //        event_collection: 'pageviews',
    //        timeframe: {
    //            start: dateStart.toISOString(),
    //            end: dateEnd.toISOString()
    //            //start: '2016-03-01T05:00:00.000Z',
    //            //end: '2016-04-01T05:00:00.000Z'
    //        },
    //        target_property: 'keen.timestamp',
    //        group_by: ['user.id', 'sessionId'],
    //        filters: [
    //            {
    //                property_name: 'user.id',
    //                operator: 'ne',
    //                property_value: 'null'
    //            }
    //        ]
    //    });
    //
    //    keenClient.run(userSessionQueryHistory, function(err, res) {
    //        if (err) {
    //            console.log('keen query error: ' + err);
    //        }
    //        else {
    //            var result = averageUserSessionLength(res);
    //            console.log(result + ' ms');
    //        }
    //    });
    //
    //    yearEnd = yearStart;
    //    monthEnd = monthStart;
    //}
}

/**
 * Retrieve data set from keen query result for further statistical processing
 *
 * @param ts
 * @returns {number}
 */
function extractDataSet(ts) {

    if (!ts) {
        return 0;
    }

    var beginTime;
    var endTime;
    var deltaSet = [];

    for ( var i in ts.result) {
        var session = ts.result[i];
        if (session.hasOwnProperty('result')) {
            if (session.result.length == 1) {
                // TODO: take care of the situation where there is only one 'keen.timestamp'
                continue;
            }
            beginTime = Date.parse(session.result[0]);
            endTime = Date.parse(session.result[session.result.length-1]);
            deltaSet.push(endTime - beginTime);
        }
    }
    return deltaSet;
}