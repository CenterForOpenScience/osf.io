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

        if (numberOfWeeks === 0) {
            var chart = self.prepareChart('keen-chart-average-session-history');
            chart.attributes({title: 'Average User/MAU Session Length History of Past 12 Weeks', width: '100%', height: '300', responsive: true});
            chart.adapter({chartType: 'columnchart'});
            chart.chartOptions({
                hAxis: {title: 'Week'},
                vAxis: {title: 'Minutes'}
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

    self.getOSFProductUsage = function() {
        var query = new Keen.Query('select_unique', {
            event_collection: 'pageviews',
            timeframe: 'previous_1_months',
            target_property: 'parsedPageUrl.path',
            group_by: ['user.id', 'parsedPageUrl.domain'],
            filters: [self.keenFilters.nullUserFilter, self.keenFilters.inactiveUserFilter]
        });

        var chartMoreThanTwo = self.prepareChart('keen-chart-osf-product-usage-mt2');
        var chartMeetings = self.prepareChart('keen-chart-osf-product-usage-mee');
        var chartPrereg = self.prepareChart('keen-chart-osf-product-usage-pre');
        var chartInstitutions = self.prepareChart('keen-chart-osf-product-usage-ins');

        var request = self.keenClient.run(query, function(error, response) {
            if (error) {
                document.getElementById('keen-chart-osf-product-usage-mt2').innerHTML = 'Keen Query Failure';
            }
            else {
                var userProductMap = self.numberOfUsers(response);
                self.drawChart(chartMoreThanTwo, 'piechart', '', [
                    {products: 'OSF Only', count: userProductMap.osf.length - userProductMap.moreThanTwo.length},
                    {products: '2+ Products', count: userProductMap.moreThanTwo.length}
                ]);
                self.drawChart(chartMeetings, 'piechart', '', [
                    {products: 'No Meetings', count: userProductMap.osf.length - userProductMap.meetings.length},
                    {products: 'Meetings', count: userProductMap.meetings.length}
                ]);
                self.drawChart(chartPrereg, 'piechart', '', [
                    {products: 'No Prereg', count: userProductMap.osf.length - userProductMap.prereg.length},
                    {products: 'Prereg', count: userProductMap.prereg.length}
                ]);
                self.drawChart(chartInstitutions, 'piechart', '', [
                    {products: 'No Institutions', count: userProductMap.osf.length - userProductMap.institutions.length},
                    {products: 'Institutions', count: userProductMap.institutions.length}
                ]);
            }
        });
    };

    self.getUserCount = function(userCount) {
        var chart = c3.generate({
            bindto: '#db-chart-user-count',
            color: {
                pattern: [
                    //rausch    hackb      kazan      babu      lima        beach     barol
                    '#ff5a5f', '#7b0051', '#007A87', '#00d1c1', '#8ce071', '#ffb400', '#b4a76c',
                    '#ff8083', '#cc0086', '#00a1b3', '#00ffeb', '#bbedab', '#ffd266', '#cbc29a',
                    '#ff3339', '#ff1ab1', '#005c66', '#00b3a5', '#55d12e', '#b37e00', '#988b4e'
                  ]},
            data: {
                json: userCount.items,
                keys: {
                    x: 'Product',
                    value: ['Count']
                },
                types: {
                    Count: 'bar'
                }
            },
            axis: {
                x: {
                    type: 'category'
                },
                rotated: true
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

    self.getUserPercentage = function(userCount) {
        var chart = c3.generate({
            bindto: '#db-chart-user-percent',
            data: {
                json: userCount.items,
                keys: {
                    x: 'Product',
                    value: ['Percentage']
                },
                types: {
                    Percentage: 'bar'
                },
                order: 'desc'
            },
            axis: {
                x: {
                    type: 'category'
                },
                rotated: true
            }
        });
    };

    self.getMultiProductCountYearly = function(multiProductMetricsYearly) {
        var chart = new keen.Dataviz()
          .el(document.getElementById('db-chart-multi-product-yearly'))
          .parseRawData({ result: multiProductMetricsYearly['multi_product_count'] })
          .chartType("metric")
          .colors(["#e57fc2"])
          .title("Users")
          .render();
      };

    self.getMultiProductCountMonthly = function(multiProductMetricsMonthly) {
        var chart = new keen.Dataviz()
          .el(document.getElementById('db-chart-multi-product-monthly'))
          .parseRawData({ result: multiProductMetricsMonthly['multi_product_count'] })
          .chartType("metric")
          .colors(["#e57fc2"])
          .title("Users")
          .render();
      };


    self.prepareChart = function(elementId) {
        var chart = new keen.Dataviz();
        return chart.el(document.getElementById(elementId)).library('c3').prepare();
    };

    self.drawChart = function(chart, type, title, result) {
        chart.attributes({title: title, width: '100%', responsive: true});
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
        self.getOSFProductUsage();
        self.getAverageUserSessionLength();
        self.getAverageMAUSessionLength();
        self.getAverageUserSessionHistory(true, 12, null, null, null);
        debugger;
        self.getUserCount(userCount);
        self.getUserPercentage(userCount);
        self.getMultiProductCountYearly(multiProductMetricsYearly);
        self.getMultiProductCountMonthly(multiProductMetricsMonthly);
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

    self.numberOfUsers = function(keenResult, filters) {
        var userProductMap = {
            'osf': [],
            'meetings': [],
            'prereg': [],
            'institutions': [],
            'moreThanTwo': []
        };
        for (var i in keenResult.result) {
            var session = keenResult.result[i];
            if (session.hasOwnProperty('result') && session.hasOwnProperty('user.id')) {
                if (session.hasOwnProperty('parsedPageUrl.domain') && session['parsedPageUrl.domain'] == 'staging.osf.io') {
                    userProductMap.osf.push(session['user.id']);
                    var paths = session['result'];
                    var numberOfProducts = 0;
                    var meetings, prereg, institutions;
                    meetings = prereg = institutions = false;
                    for (var i in paths) {
                        if (meetings == false && paths[i].startsWith('/meetings/')) {
                            userProductMap.meetings.push(session['user.id']);
                            meetings = true;
                            numberOfProducts ++;
                        }
                        else if (prereg == false && paths[i].startsWith('/prereg/')) {
                            userProductMap.prereg.push(session['user.id']);
                            prereg = true;
                            numberOfProducts ++;
                        }
                        else if (institutions == false && paths[i].startsWith('/institutions/')) {
                            userProductMap.institutions.push(session['user.id']);
                            meetings = true;
                            numberOfProducts ++;
                        }
                    }
                    if (numberOfProducts > 0) {
                        userProductMap.moreThanTwo.push(session['user.id']);
                    }
                }
            }
        }
        return userProductMap;
    };
};

var salesAnalytics = new SalesAnalytics();
salesAnalytics.init();
