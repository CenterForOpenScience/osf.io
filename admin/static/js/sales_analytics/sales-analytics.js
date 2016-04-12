'use strict';

var keen = require('keen-js');

keen.ready(function(){

    var keenClient = new keen({
        //  TODO: use view context to pass settings.KEEN_PROJECT_ID and settings.KEEN_READ_KEY
        //projectId: 'changeme',
        //readKey : 'changeme'
    });

    //  query for average user session length
    var userSessionQuery = new keen.Query('select_unique', {
        event_collection: 'pageviews',
        //timeframe: 'previous_7_days',
        timeframe: 'previous_1_months',
        target_property: 'keen.timestamp',
        group_by: ['user.id', 'sessionId'],
        filters: [
            {
                property_name: 'user.id',
                operator: 'ne',
                property_value: 'null'
            }
        ]
    });

    //  query for average MAU (monthly active user) session length
    var activeUserSessionQuery = new keen.Query('select_unique', {
        event_collection: 'pageviews',
        //timeframe: 'previous_7_days',
        timeframe: 'previous_1_months',
        target_property: 'keen.timestamp',
        group_by: ['user.id', 'sessionId'],
        filters: [
            {
                property_name: 'user.id',
                operator: 'ne',
                property_value: 'null'
            },
            {
                property_name: 'user.id',
                operator: 'ne',
                property_value: ''
            }
        ]
    });

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
            var result1 = averageUserSessionLength(res[0]);
            var result2 = averageUserSessionLength(res[1]);
            console.log('average user session length is ' + result1 + " ms" );
            console.log('average user session length (mau) is ' + result2 + " ms" );

            chartAverageSessionUser.attributes({ title: 'Average User Session Length in Minutes', width: 800 });
            chartAverageSessionUser.adapter({chartType: 'metric'});
            chartAverageSessionMAU.attributes({ title: 'Average MAU Session Length in Minutes', width: 800 });
            chartAverageSessionUser.parseRawData({result: result1/1000/60});
            chartAverageSessionMAU.parseRawData({result: result2/1000/60});
            chartAverageSessionUser.render();
            chartAverageSessionMAU.render();
        }
    });

    setInterval(function() {
        console.log('chart refresh');
        req.refresh();
    }, 1000 * 60);


    //  average user/mau session length each month for the past 12 months
    var date = new Date();
    var yearEnd = date.getFullYear();
    var monthEnd = date.getMonth();

    var count = 12;
    //yearEnd = monthEnd - 1 < 0 ? yearEnd-1 : yearEnd;
    //monthEnd = (monthEnd - 1) % 12;
    while (count-- > 0) {
        var yearStart = yearEnd - 1 < 0 ? yearEnd - 1 : yearEnd;
        var monthStart = (monthEnd - 1) % 12;

        var dateStart = new Date(yearStart, monthStart, 1);
        var dateEnd = new Date(yearEnd, monthEnd, 1);

        console.log(dateStart.toISOString());
        console.log(dateEnd.toISOString());

        var userSessionQueryHistory = new keen.Query('select_unique', {
            event_collection: 'pageviews',
            timeframe: {
                start: dateStart.toISOString(),
                end: dateEnd.toISOString()
                //start: '2016-03-01T05:00:00.000Z',
                //end: '2016-04-01T05:00:00.000Z'
            },
            target_property: 'keen.timestamp',
            group_by: ['user.id', 'sessionId'],
            filters: [
                {
                    property_name: 'user.id',
                    operator: 'ne',
                    property_value: 'null'
                }
            ]
        });

        keenClient.run(userSessionQueryHistory, function(err, res) {
            if (err) {
                console.log('keen query error: ' + err);
            }
            else {
                var result = averageUserSessionLength(res);
                console.log(result + ' ms');

                //  TODO: Use Keenviz for visualization
            }
        });

        yearEnd = yearStart;
        monthEnd = monthStart;
        //break;
    }
});

/**
 * A simple function to calculate the average of user session time.
 * TODO: use stats/math lib to generate more meaningful results.
 *
 * @param ts
 * @returns {number}
 */
function averageUserSessionLength(ts) {

    if (!ts) {
        return 0;
    }

    var beginTime;
    var endTime;
    var sumOfDelta = 0;
    var numOfSessions = 0;

    for ( var i in ts.result) {
        var session = ts.result[i];
        if (session.hasOwnProperty('result')) {
            beginTime = Date.parse(session.result[0]);
            endTime = Date.parse(session.result[session.result.length-1]);
            sumOfDelta += endTime - beginTime;
            numOfSessions ++;
        }
    }

    return sumOfDelta/numOfSessions;
}