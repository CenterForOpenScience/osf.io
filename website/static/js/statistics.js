'use strict';

var keenAnalysis = require('keen-analysis');
var keenDataviz = require('keen-dataviz');
require('keen-dataviz/dist/keen-dataviz.min.css');
var ko = require('knockout');
var ctx = window.contextVars;
var $osf = require('js/osfHelpers');

var KeenViz = function(){
    var self = this;

    self.keenClient = new keenAnalysis({
        projectId: ctx.keenProjectId,
        readKey : ctx.keenReadKey
    });

    self.visitsByDay = function() {
        var visitsQuery = {
            'queryType':'count_unique',
            'queryParams' : {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                interval: 'daily',
                target_property: 'sessionId'
            }
        };

        var visitsViz = new keenDataviz().chartOptions({
            tooltip: {
                format: {
                    name: function(){return 'Visits';}
                }
            }
        });

        var params = {
            keenDataviz: visitsViz,
            selector: '#visits',
            keenQuery: visitsQuery
        };
        self.chart(params);

    };

    self.topReferrers = function() {
        self.referrers = ko.observableArray([]);
        self.loadRefs = ko.observable(true);

        var topReferrersQuery = {
            'queryType': 'count_unique',
            'queryParams': {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                target_property: 'user.id',
                group_by: 'parsedReferrerUrl.domain'
            }
        };

        var req = self.keenClient
            .query(topReferrersQuery.queryType, topReferrersQuery.queryParams)
            .then(function(res) {
                self.parseTopReferrers(res.result);
                self.loadRefs(false);
            })
            .catch(function(err){
                new keenDataviz.el('#topReferrers').message(err.message);
            });

        $osf.applyBindings(self, '#topReferrers');
    };

    self.parseTopReferrers = function(data){
        self.referrers(
            (function(){
            return data.map(function(obj){
                return {
                    'referrer': obj['parsedReferrerUrl.domain'],
                    'count': obj.result
                };
            });}())
        );

    };

    self.visitsServerTime = function() {
        var serverTimeVisitsQuery = {
            'queryType': 'count_unique',
            'queryParams': {
                event_collection: 'pageviews',
                timeframe: 'this_1_days',
                interval: 'hourly',
                target_property: 'sessionId'
            }
        };

        var serverVisitsViz = new keenDataviz().chartOptions({
            tooltip:{
                format:{
                    name: function(){return 'Visits';}
                }
            }
        });
        serverVisitsViz.chartType('bar');
        var params = {
            keenDataviz: serverVisitsViz,
            selector: '#serverTimeVisits',
            keenQuery: serverTimeVisitsQuery
        };
        self.chart(params);

    };

    self.chart = function(params){

        params.keenDataviz.el(params.selector);

        self.keenClient
            .query(params.keenQuery.queryType, params.keenQuery.queryParams)
            .then(function(res){
                params.keenDataviz.title(' ').data(res).render();
            })
            .catch(function(err){
                params.keenDataviz.message(err.message);
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
