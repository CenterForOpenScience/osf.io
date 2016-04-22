'use strict';

var c3 = require('c3');
var keen = require('keen-js');
var ss = require('simple-statistics');

var SalesAnalytics = function() {
    var self = this;

    self.keenClient = new keen({
        projectId: keenProjectId,
        readKey : keenReadKey
    });

    self.keenFilters = {
        nullUserFilter: {
            property_name: 'user.id',
            operator: 'ne',
            property_value: 'null'
        },
        inactiveUserFilter: {
            property_name: 'user.id',
            operator: 'ne',
            property_value: ''
        }
    };

    self.getAverageUserSessionLength = function () {
        var query = new keen.Query('select_unique', {
            event_collection: 'pageviews',
            timeframe: 'previous_7_days',
            target_property: 'keen.timestamp',
            group_by: ['user.id', 'sessionId'],
            filters: [self.keenFilters.nullUserFilter]
        });

        var chart = new keen.Dataviz();
        chart.el(document.getElementById('keen-chart-average-session-user')).prepare();

        var request = self.keenClient.run(query, function(error, response) {
            if (error) {
                document.getElementById('keen-chart-average-session-user').innerHTML = 'Keen Query Failure';
                console.log(error);
            }
            else {
                var dataSet = self.extractDataSet(response);
                var result = ss.mean(dataSet);
                console.log('average user session length is ' + result + " ms" );

                chart.attributes({ title: 'Average User Session Length', width: 600 });
                chart.adapter({chartType: 'metric'});
                chart.parseRawData({result: result/1000/60});
                chart.render();
            }
        });
    };

    self.getAverageMAUSessionLength = function() {
        var query = new keen.Query('select_unique', {
            event_collection: 'pageviews',
            timeframe: 'previous_7_days',
            target_property: 'keen.timestamp',
            group_by: ['user.id', 'sessionId'],
            filters: [self.keenFilters.nullUserFilter, self.keenFilters.inactiveUserFilter]
        });

        var chart = new keen.Dataviz();
        chart.el(document.getElementById('keen-chart-average-session-mau')).prepare();

        var request = self.keenClient.run(query, function(error, response) {
            if (error) {
                document.getElementById('keen-chart-average-session-mau').innerHTML = 'Keen Query Failure';
                console.log(error);
            }
            else {
                var dataSet = self.extractDataSet(response);
                var result = ss.mean(dataSet);
                console.log('average mau session length is ' + result + " ms" );

                chart.attributes({ title: 'Average MAU Session Length', width: 600 });
                chart.adapter({chartType: 'metric'});
                chart.parseRawData({result: result/1000/60});
                chart.render();
            }
        });
    };

    self.getAverageUserSessionHistory = function(init, numberOfWeeks, weekEnd, weekStart, weeklyResult) {
        if (init == true) {
            var date = new Date();
            date.setHours(0, 0, 0, 0);
            date.setDate(date.getDate() - date.getDay());
            weekEnd = new Date(date);
            weekStart = new Date(date.setDate(date.getDate() - 7));
            weeklyResult = [];
            self.getAverageUserSessionHistory(false, numberOfWeeks, weekEnd, weekStart, weeklyResult);
            return;
        }

        if (numberOfWeeks == 0) {
            var chart = new keen.Dataviz();
            chart.el(document.getElementById('keen-chart-average-session-history')).prepare();
            chart.attributes({title: 'Average User Session History of the Past 12 Weeks', width: 1000, height: 500});
            chart.adapter({chartType: 'columnchart'});
            chart.chartOptions({
                hAxis: {
                    title: "Week"
                },
                vAxis: {
                    title: "Minutes"
                }
            });

            chart.parseRawData({result: weeklyResult});
            chart.render();
            return;
        }

        console.log(numberOfWeeks + ': ' + weekEnd.toISOString());
        document.getElementById('keen-chart-average-session-history').innerHTML = numberOfWeeks;

        var queryUser = new keen.Query('select_unique', {
            event_collection: 'pageviews',
            timeframe: {
                start: weekStart.toISOString(),
                end: weekEnd.toISOString()
            },
            target_property: 'keen.timestamp',
            group_by: ['user.id', 'sessionId'],
            filters: [self.keenFilters.nullUserFilter]
        });

        var queryMAU = new keen.Query('select_unique', {
            event_collection: 'pageviews',
            timeframe: {
                start: weekStart.toISOString(),
                end: weekEnd.toISOString()
            },
            target_property: 'keen.timestamp',
            group_by: ['user.id', 'sessionId'],
            filters: [self.keenFilters.nullUserFilter, self.keenFilters.inactiveUserFilter]
        });

        var request = self.keenClient.run([queryUser, queryMAU], function (error, response) {
            var resultUser;
            var resultMAU;
            if (error) {
                document.getElementById('keen-chart-average-session-history').innerHTML = 'Keen Query Failure';
                console.log(error);
                //resultUser = resultMAU = -1;
            }
            else {
                var dataSetUser = self.extractDataSet(response[0]);
                var dataSetMAU = self.extractDataSet(response[1]);
                resultUser = ss.mean(dataSetUser);
                resultMAU = ss.mean(dataSetMAU);
            }
            var item = {
                timeframe: {
                    start: weekStart.toISOString(),
                    end: weekEnd.toISOString()
                },
                value: [
                    { category: 'User', result: resultUser/1000/60 },
                    { category: 'MAU', result: resultMAU/1000/60 }
                ]
            };
            weeklyResult.push(item);

            weekEnd = new Date(weekStart);
            weekStart.setDate(weekEnd.getDate() - 7);
            numberOfWeeks--;
            self.getAverageUserSessionHistory(false, numberOfWeeks, weekEnd, weekStart, weeklyResult);
        });
    };

    self.getUserCount = function(userCount) {
        var chart = c3.generate({
            bindto: '#db-chart-user-count',
            data: {
                json: userCount.items,
                type: 'bar',
                keys: {
                    x: 'Product',
                    value: ['Count']
                },
            },
            axis: {
                x: {
                    type: 'category'
                }
            },
            bar: {
                width: {
                    ratio: 0.5 // this makes bar width 50% of length between ticks
                }
                // or
                //width: 100 // this makes bar width 100px
            }
        });
    };

    self.init = function() {
        console.log('init');
        keen.ready(self.run());
    };

    self.run = function() {
        console.log('run');
        self.getAverageUserSessionLength();
        self.getAverageMAUSessionLength();
        self.getAverageUserSessionHistory(true, 12, null, null, null);
        self.getUserCount(userCount);
    };

    self.clean = function() {
        console.log('clean');
    };

    self.extractDataSet = function(keenResult) {
        if (!keenResult) {
            return 0;
        }

        var beginTime;
        var endTime;
        var deltaSet = [];

        for ( var i in keenResult.result) {
            var session = keenResult.result[i];
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
    };
};

var salesAnalytics = new SalesAnalytics();
salesAnalytics.init();
