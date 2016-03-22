"use strict";

var keen = require('keen-js');
var ctx = window.contextVars;

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
            target_property: 'sessionId',
            filters: [
                {
                    property_name: 'node.id',
                    operator: 'eq',
                    property_value: ctx.node.id
                }
            ]
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
        var topReferrersQuery = new keen.Query('count', {
            event_collection: 'pageviews',
            timeframe: 'this_7_days',
            group_by: 'parsedReferrerUrl.domain',
            filters: [
                {
                    property_name: 'node.id',
                    operator: 'eq',
                    property_value: ctx.node.id
                }
            ]
        });

        var topReferrersViz = new keen.Dataviz();
        var params = {
            keenDataviz: topReferrersViz,
            selector: 'topReferrers',
            keenQuery: topReferrersQuery,
            adapterOptions: {
                chartType: 'table'
            },
            chartOptions: {
                cssClassNames: {
                    headerRow: "test"
                }
            }
        };
        self.chart(params);

    };

    self.visitsServerTime = function() {
        var serverTimeVisitsQuery = new keen.Query('count_unique', {
            event_collection: 'pageviews',
            timeframe: 'this_1_days',
            interval: 'hourly',
            target_property: 'sessionId',
            filters: [
                {
                    property_name: 'node.id',
                    operator: 'eq',
                    property_value: ctx.node.id
                }
            ]
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
        params.keenDataviz.el(document.getElementById(params.selector))
            .height(300)
            .prepare();

        var req = self.keenClient.run(params.keenQuery, function(err, res){
            if (err){
                params.keenDataviz.error(err.message);
            }
            else {
                debugger;
                params.keenDataviz.parseRequest(this)
                    .adapter(params.adapterOptions || {})
                    .chartOptions(params.chartOptions || {})
                    .render();
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
