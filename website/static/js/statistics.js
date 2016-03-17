"use strict";

var keen = require('keen-js');
var ctx = windows.contextVars;

var KeenViz = function(){
    var self = this;

    self.keenClient = new keen({
        projectId: ctx.keenProjectId,
        writeKey: ctx.keenWriteKey
    });

    self.keenDataviz = new keen.Dataviz();

    self.visitsByDay = function() {
        var query = new self.keenClient.Query('count_unique', {
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

        self.keenDataviz.el(document.getElementById('visits'))
            .height(600)
            .prepare();

        var req = self.keenClient.run(query, function(err, res){
            if (err){
                self.keenDataviz.error(err.message);
            }
            else {
                self.keenDataviz.parseRequest(this)
                    .title('Visits for ' + ctx.node.id)
                    .render();
            }
        })
    }


};
