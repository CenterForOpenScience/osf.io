'use strict';

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
            property_value: null
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

        var chart = self.prepareChart('keen-chart-average-session-user');

        self.keenClient.run(query, function(error, response) {
            if (error) {
                document.getElementById('keen-chart-average-session-user').innerHTML = 'Keen Query Failure';
                console.log(error);
            }
            else {
                var dataSet = self.extractDataSet(response);
                var result = ss.mean(dataSet);
                self.drawChart(chart, 'metric', 'Minutes', result/1000/60);
                console.log('average user session length is ' + result + " ms" );
            }
        });
    };

    // TODO: add functionality to let user choose what to query
    self.getAverageMAUSessionLength = function() {
        var query = new keen.Query('select_unique', {
            event_collection: 'pageviews',
            timeframe: 'previous_7_days',
            target_property: 'keen.timestamp',
            group_by: ['user.id', 'sessionId'],
            filters: [self.keenFilters.nullUserFilter, self.keenFilters.inactiveUserFilter]
        });

        var chart = self.prepareChart('keen-chart-average-session-mau');

        self.keenClient.run(query, function(error, response) {
            if (error) {
                document.getElementById('keen-chart-average-session-mau').innerHTML = 'Keen Query Failure.';
                console.log(error);
            }
            else {
                var dataSet = self.extractDataSet(response);
                var result = ss.mean(dataSet);
                console.log('average mau session length is ' + result + " ms" );
                self.drawChart(chart, 'metric', 'Minutes', result/1000/60);
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
            var chart = self.prepareChart('keen-chart-average-session-history');
            chart.attributes({title: 'Average User/MAU Session Length History of Past 12 Weeks', width: 600, height: 450});
            chart.adapter({chartType: 'columnchart'});
            chart.chartOptions({
                hAxis: {title: "Week"},
                vAxis: {title: "Minutes"}
            });
            chart.parseRawData({result: weeklyResult}).render();
            return;
        }

        document.getElementById('keen-chart-average-session-history').innerHTML = 'loading ... : ' + (12 - numberOfWeeks) + ' / 12';
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

        self.keenClient.run([queryUser, queryMAU], function (error, response) {
            var resultUser;
            var resultMAU;
            if (error) {
                document.getElementById('keen-chart-average-session-history').innerHTML = 'failure ... : ' + (12 - numberOfWeeks) + ' / 12';
                console.log(error);
                resultUser = resultMAU = -1;
            }
            else {
                var dataSetUser = self.extractDataSet(response[0]);
                var dataSetMAU = self.extractDataSet(response[1]);
                resultUser = ss.mean(dataSetUser);
                resultMAU = ss.mean(dataSetMAU);
                console.log('Week ' + numberOfWeeks + ' (' + weekEnd.toISOString() + '): ' + resultUser + ', ' + resultMAU);
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

    self.prepareChart = function(elementId) {
        var chart = new keen.Dataviz();
        return chart.el(document.getElementById(elementId)).prepare();
    };

    self.drawChart = function(chart, type, title, result) {
        chart.attributes({title: title, width: 600});
        chart.adapter({chartType: type});
        chart.parseRawData({result: result});
        chart.render();
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

        for (var i in keenResult.result) {
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