'use strict';

var keenAnalysis = require('keen-analysis');
var keenDataviz = require('keen-dataviz');
require('keen-dataviz/dist/keen-dataviz.min.css');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

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
                target_property: 'visitor.session'
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
        self.referrers = ko.observableArray([]);
        self.loadRefs = ko.observable(true);

        var topReferrersQuery = {
            'queryType': 'count_unique',
            'queryParams': {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                target_property: 'keen.id',
                group_by: 'referrer.info.domain'
            }
        };

        var req = self.keenClient
            .query(topReferrersQuery.queryType, topReferrersQuery.queryParams)
            .then(function(res) {
                self.parseTopReferrers(res.result);
                self.loadRefs(false);
            })
            .catch(function(err){
                new keenDataviz().el('#topReferrers').message(err.message);
            });

        $osf.applyBindings(self, '#topReferrers');
    };

    self.parseTopReferrers = function(data){
        self.referrers(
            (function(){
            return data.map(function(obj){
                return {
                    'referrer': obj['referrer.info.domain'],
                    'count': obj.result
                };
            });}())
        );

    };

    self.visitsServerTime = function() {
        var serverTimeVisitsQuery = {
            'type': 'count_unique',
            'params': {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                target_property: 'keen.id',
                group_by: 'time.local.hour_of_day',
            }
        };

        var serverVisitsViz = new keenDataviz()
                .el('#serverTimeVisits')
                .chartType('bar')
                .chartOptions({
                    tooltip:{
                        format:{
                            name: function(){return 'Visits';}
                        }
                    }
                });
        self.buildChart(serverVisitsViz, serverTimeVisitsQuery);

    };

    self.buildChart = function(dataviz, query){
        self.keenClient
            .query(query.type, query.params)
            .then(function(res) {
                dataviz.title(' ').data(res).render();
            })
            .catch(function(err) {
                dataviz.message(err.message);
            });
    };

    self.init = function () {
        self.visitsByDay();
        self.topReferrers();
        self.visitsServerTime();
    };


};

function ProjectUsageStatistics() {
    var self = this;
    self.KeenViz = new KeenViz();
    self.KeenViz.init();
}

module.exports = ProjectUsageStatistics;
