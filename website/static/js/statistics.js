'use strict';

require('keen-dataviz/dist/keen-dataviz.min.css');

var $osf = require('js/osfHelpers');
var keenDataviz = require('keen-dataviz');
var keenAnalysis = require('keen-analysis');

var KeenViz = function(){
    var self = this;

    self.keenClient = new keenAnalysis({
        projectId: window.contextVars.keen.public.projectId,
        readKey : window.contextVars.keen.public.readKey,
    });

    self.visitsByDay = function() {
        var visitsQuery = {
            'type':'count_unique',
            'params' : {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                interval: 'daily',
                target_property: 'anon.id'
            }
        };

        var visitsViz = new keenDataviz()
                .el('#visits')
                .chartType('line')
                .chartOptions({
                    tooltip: {
                        format: {
                            name: function(){return 'Visits';}
                        }
                    }
                });

        self.buildChart(visitsViz, visitsQuery);
    };

    self.topReferrers = function() {
        var topReferrersQuery = {
            type: 'count_unique',
            params: {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                target_property: 'anon.id',
                group_by: 'referrer.info.domain'
            }
        };

        var topReferrersViz = new keenDataviz()
                .el('#topReferrers')
                .chartType('pie')
                .chartOptions({
                    tooltip:{
                        format:{
                            name: function(){return 'Visits';}
                        }
                    },
                });

        self.buildChart(topReferrersViz, topReferrersQuery);
    };

    self.visitsServerTime = function() {
        var query = {
            'type': 'count_unique',
            'params': {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                target_property: 'anon.id',
                group_by: 'time.local.hour_of_day',
            }
        };

        var dataviz = new keenDataviz()
                .el('#serverTimeVisits')
                .chartType('bar')
                .chartOptions({
                    tooltip:{
                        format:{
                            name: function(){return 'Visits';}
                        }
                    },
                    axis: {
                        x: {
                            label: {
                                text: 'Hour of Day',
                                position: 'outer-center',
                            },
                            tick: {
                                centered: true,
                                values: ['0', '4', '8', '12', '16', '20'],
                            },
                        },
                    },
                });

        var munger = function() {
            var foundHours = {};
            for (var i=this.dataset.matrix.length-1; i>0; i--) {
                var row = this.dataset.selectRow(i);
                foundHours[ row[0] ] = row[1];
                this.dataset.deleteRow(i);
            }

            for (var hour=0; hour<24; hour++) {
                var stringyNum = '' + hour;
                this.dataset.appendRow(stringyNum, [ foundHours[stringyNum] || 0 ]);
            }
        };
        self.buildChart(dataviz, query, munger);

    };

    self.popularPages = function() {
        var popularPagesQuery = {
            type: 'count_unique',
            params: {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                target_property: 'anon.id',
                group_by: 'page.title'
            }
        };

        var popularPagesViz = new keenDataviz()
                .el('#popularPages')
                .chartType('bar')
                .chartOptions({
                    tooltip:{
                        format:{
                            name: function(){return 'Visits';}
                        }
                    }
                });

        self.buildChart(popularPagesViz, popularPagesQuery);
    };

    self.buildChart = function(dataviz, query, munger){
        munger = munger || function() {};

        self.keenClient
            .query(query.type, query.params)
            .then(function(res) {
                dataviz.title(' ').data(res).call(munger).render();
            })
            .catch(function(err) {
                dataviz.message(err.message);
            });
    };

    self.init = function () {
        self.visitsByDay();
        self.topReferrers();
        self.visitsServerTime();
        self.popularPages();
    };


};

function ProjectUsageStatistics() {
    var self = this;
    self.KeenViz = new KeenViz();
    self.KeenViz.init();
}

module.exports = ProjectUsageStatistics;
