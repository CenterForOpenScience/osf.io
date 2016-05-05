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

    self.getOSFProductView = function() {
        var query = new Keen.Query('select_unique', {
            event_collection: 'pageviews',
            timeframe: 'previous_1_months',
            target_property: 'parsedPageUrl.path',
            group_by: ['user.id', 'parsedPageUrl.domain'],
            filters: [self.keenFilters.nullUserFilter, self.keenFilters.inactiveUserFilter]
        });

        var chartMoreThanTwo = self.prepareChart('keen-chart-osf-products-view-mt2');
        var chartMeetings = self.prepareChart('keen-chart-osf-products-view-mee');
        var chartPrereg = self.prepareChart('keen-chart-osf-products-view-pre');
        var chartInstitutions = self.prepareChart('keen-chart-osf-products-view-ins');

        var request = self.keenClient.run(query, function(error, response) {
            if (error) {
                console.log(error);
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
        self.getOSFProductView();
    };

    self.clean = function() {
        console.log('clean');
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
                    for (var j in paths) {
                        if (meetings == false && paths[j].startsWith('/meetings/')) {
                            userProductMap.meetings.push(session['user.id']);
                            meetings = true;
                            numberOfProducts ++;
                        }
                        else if (prereg == false && paths[j].startsWith('/prereg/')) {
                            userProductMap.prereg.push(session['user.id']);
                            prereg = true;
                            numberOfProducts ++;
                        }
                        else if (institutions == false && paths[j].startsWith('/institutions/')) {
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
