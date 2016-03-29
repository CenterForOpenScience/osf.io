"use strict";

var keen = require('keen-js');
var ko = require('knockout');
var ctx = window.contextVars;
var $osf = require("js/osfHelpers");

var KeenViz = function(){
    var self = this;

    self.keenClient = new keen({
        projectId: ctx.keenProjectId,
        readKey : ctx.keenReadKey
    });

    self.visitsByDay = function() {
        var visitsQuery = new keen.Query('count_unique', {
            event_collection: 'pageviews',
            timeframe: 'this_7_days',
            interval: 'daily',
            target_property: 'sessionId'
        });

        var visitsViz = new keen.Dataviz();
        var params = {
            keenDataviz: visitsViz,
            selector: 'visits',
            keenQuery: visitsQuery
        };
        self.chart(params);

    };

    self.topReferrers = function() {
        self.referrers = ko.observableArray([]);
        self.loadRefs = ko.observable(true);

        var topReferrersQuery = new keen.Query('count_unique', {
            event_collection: 'pageviews',
            timeframe: 'this_7_days',
            target_property: 'user.id',
            group_by: 'parsedReferrerUrl.domain'
        });

        var req = self.keenClient.run(topReferrersQuery, function(err, res){
            if (err){
                new keen.Dataviz().el(document.getElementById('topReferrers')).error(err.message);
            } else {
                self.parseTopReferrers(res.result);
                self.loadRefs(false);
            }
        });

        $osf.applyBindings(self, '#topReferrers');
    };

    self.parseTopReferrers = function(data){
        self.referrers(function(){
            return data.map(function(obj){
                return {
                    'referrer': obj['parsedReferrerUrl.domain'],
                    'count': obj.result
                };
            });
        }());

    };

    self.visitsServerTime = function() {
        var serverTimeVisitsQuery = new keen.Query('count_unique', {
            event_collection: 'pageviews',
            timeframe: 'this_1_days',
            interval: 'hourly',
            target_property: 'sessionId'
        });

        var serverVisitsViz = new keen.Dataviz();
        serverVisitsViz.chartType('columnchart');
        var params = {
            keenDataviz: serverVisitsViz,
            selector: 'serverTimeVisits',
            keenQuery: serverTimeVisitsQuery
        };
        self.chart(params);

    };

    self.chart = function(params){

        params.keenDataviz.el(document.getElementById(params.selector));

        var req = self.keenClient.run(params.keenQuery, function(err, res){
            if (err){
                params.keenDataviz.error(err.message);
            }
            else {
                params.keenDataviz.parseRequest(this).render();
            }
        });
    };

    self.init = function () {
        self.visitsByDay();
        self.topReferrers();
        self.visitsServerTime();
    }


};

function Statistics() {
    var self = this;
    self.KeenViz = new KeenViz();
    self.KeenViz.init();
    setInterval(function() {
        self.KeenViz.init();
    }, 1000*60*15);
}

module.exports = Statistics;
