'use strict';

require('keen-dataviz/dist/keen-dataviz.min.css');

var $osf = require('js/osfHelpers');
var keenDataviz = require('keen-dataviz');
var keenAnalysis = require('keen-analysis');

var KeenViz = function(){
    var self = this;

    /**
    * Manages the connections to Keen.  Needs a project id and valid read key for that project.
    *
    * @property keenClient
    * @type {keenAnalysis}
    */
    self.keenClient = new keenAnalysis({
        projectId: window.contextVars.keen.public.projectId,
        readKey : window.contextVars.keen.public.readKey,
    });


    // show visits to this project over the last week
    self.visitsByDay = function() {
        var query = {
            'type':'count_unique',
            'params' : {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                interval: 'daily',
                target_property: 'anon.id'
            }
        };

        var dataviz = new keenDataviz()
                .el('#visits')
                .chartType('line')
                .chartOptions({
                    tooltip: {
                        format: {
                            name: function(){return 'Visits';}
                        }
                    }
                });

        self.buildChart(query, dataviz);
    };


    // show most common referrers to this project from the last week
    self.topReferrers = function() {
        var query = {
            type: 'count_unique',
            params: {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                target_property: 'anon.id',
                group_by: 'referrer.info.domain'
            }
        };

        var dataviz = new keenDataviz()
                .el('#topReferrers')
                .chartType('pie')
                .chartOptions({
                    tooltip:{
                        format:{
                            name: function(){return 'Visits';}
                        }
                    },
                });

        self.buildChart(query, dataviz);
    };

    // The number of visits by hour across last week
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

        // make sure all hours of the day 0-23 are present
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
        self.buildChart(query, dataviz, munger);

    };

    // most popular sub-pages of this project
    self.popularPages = function() {
        var query = {
            type: 'count_unique',
            params: {
                event_collection: 'pageviews',
                timeframe: 'this_7_days',
                target_property: 'anon.id',
                group_by: 'page.title'
            }
        };

        var dataviz = new keenDataviz()
                .el('#popularPages')
                .chartType('bar')
                .chartOptions({
                    tooltip:{
                        format:{
                            name: function(){return 'Visits';}
                        }
                    }
                });

        var munger = function() {
            this.dataset.updateColumn(0, function(value, index, column) {
                var title = value.replace(/^OSF \| /, '');
                // Strip off the project title, if present at beginning of string
                if (title.startsWith(window.contextVars.node.title)) {
                    // strip off first N chars where N is project title length + 1 space
                    var pageTitleIndex = window.contextVars.node.title.length + 1;
                    title = title.slice(pageTitleIndex);
                }
                return title || 'Home';
            });
        };

        self.buildChart(query, dataviz, munger);
    };


    /**
     * Build a data chart on the page. The element on the page that the chart will be inserted into
     * is defined in the `dataviz` parameter. A spinner will be displayed while the data is being
     * loaded.  If an error is returned, it will be displayed within the chart element.
     *
     * @method buildChart
     * @param {Object} query Defines the analysis to relay to Keen. Has two top-level keys, `type`
     *                       and `params`. `type` is the type of aggregation to perform. `params`
     *                       defines the parameters of the query.  See:
     *                       https://keen.io/docs/api/?javascript#analyses
     * @param {Keen.Dataviz} dataviz The Dataviz object that defines the look chart. See:
     *                               https://github.com/keen/keen-dataviz.js/tree/master/docs
     * @param {Function} [munger] *optional* A function that can munge the Keen.Dataset returned
     *                            from the query.  Useful for formatting data before display. See:
     *                            https://github.com/keen/keen-dataviz.js/tree/master/docs/dataset
     */
    self.buildChart = function(query, dataviz, munger){
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

    self.drawAllCharts = function () {
        self.visitsByDay();
        self.topReferrers();
        self.visitsServerTime();
        self.popularPages();
    };


};

function ProjectUsageStatistics() {
    var self = this;
    self.keenViz = new KeenViz();
}

module.exports = ProjectUsageStatistics;
