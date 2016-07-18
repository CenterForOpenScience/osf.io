'use strict';

require('keen-dataviz/dist/keen-dataviz.min.css');

var oop = require('js/oop');
var $osf = require('js/osfHelpers');
var keenDataviz = require('keen-dataviz');
var keenAnalysis = require('keen-analysis');


var UserFacingChart = oop.defclass({
    constructor: function(params) {
        var self = this;
        params = params || {};

        var required = ['keenProjectId', 'keenReadKey', 'containingElement'];
        required.forEach(function(paramName) {
            if (!params[paramName]) {
                throw 'Missing required argument "' + paramName + '"';
            }
        });

        /**
         * Manages the connections to Keen.  Needs a project id and valid read key for that project.
         *
         * @property keenClient
         * @type {keenAnalysis}
         */
        self.keenClient = new keenAnalysis({
            projectId: params.keenProjectId,
            readKey: params.keenReadKey,
        });

        /**
         * HTML id of containing element.
         *
         * @property containingElement
         * @type {string}
         */
        self.containingElement = params.containingElement;

        /**
         * Max number of entries to display for category-based charts. Ignored for time-series data.
         * Default 10.
         *
         * @property MAX_DISPLAY_ENTRIES
         * @type {integer}
         */
        self.MAX_DISPLAY_ENTRIES = params.maxDisplayEntries || 10;
    },

    /**
     * Returns an Object that defines the analysis to relay to Keen. Has two top-level keys,
     * `type` and `params`. `type` is the type of aggregation to perform. `params` defines the
     * parameters of the query.  The timeframe for the analysis is be filled in by the query()
     * method, which calls baseQuery().
     *
     * See: https://keen.io/docs/api/?javascript#analyses
     *
     * @method baseQuery
     * @return {Object}
     */
    baseQuery: function() {
        throw 'Concrete class does not provide a "baseQuery" method!';
    },

    /**
     * Calls the concrete class's baseQuery() and adds the timeframe for the analysis. The start
     * and end dates of the timeframe come from the startDate and endDate parameters saved with
     * the chart.
     *
     * @method query
     * @return {Object}
     */
    query: function() {
        var self = this;

        var baseQuery = self.baseQuery();
        baseQuery.params.timeframe = {
            start: self.startDate.toISOString(),
            end: self.endDate.toISOString(),
        };
        return baseQuery;
    },
    _initDataviz: function() {
        var self = this;
        return new keenDataviz().el(self.containingElement);
    },

    /**
     * A function that is called after the data from the query is set, but before the chart is
     * rendered.  Can be used to modify the data before displaying.  The data is available in the
     * `self.chart.dataset` object.  This object and the methods available on it are described here:
     *
     * https://github.com/keen/keen-dataviz.js/tree/master/docs/dataset
     *
     * Defaults to a no-op function.
     *
     * @method munger
     * @return {null}
     */
    munger: function() { },


    /**
     * Sets the date range over which the metric should apply.  Sets the startDate and endDate
     * properties.  These 
     *
     * @method setDataRange
     * @param {Date} startDate first day (inclusive) for which to display stats
     * @param {Date} endDate last day (exclusive) for which to display stats
     * @return {null}
     */
    setDateRange: function(startDate, endDate) {
        var self = this;
        self.startDate = startDate;
        self.endDate = endDate;
    },

    /**
     * Build a data chart on the page. The element on the page that the chart will be inserted into
     * is defined in the `dataviz` parameter. A spinner will be displayed while the data is being
     * loaded.  If an error is returned, it will be displayed within the chart element.
     *
     * @method buildChart
     * @param {Keen.Dataviz} dataviz The Dataviz object that defines the look chart. See:
     *                               https://github.com/keen/keen-dataviz.js/tree/master/docs
     */
    buildChart: function() {
        var self = this;
        if (!self.chart) {
            self.chart = self._initDataviz();
        }

        self.chart.prepare();
        var query = self.query();
        self.keenClient
            .query(query.type, query.params)
            .then(function(res) {
                self.chart.title(' ').data(res).call(self.munger.bind(self)).render();
            })
            .catch(function(err) {
                self.chart.message(err.message);
            });
    },

    // helpers functions to format raw data
    _helpers: {
        // hide non-integer labels on charts for counts
        hideNonIntegers: function(d) {
            return (parseInt(d) === d) ? d : null;
        },
    },


});


// show unique visits to this project
var ChartUniqueVisits = oop.extend(UserFacingChart, {
    constructor: function(params) {
        this.super.constructor.call(this, params);
    },
    baseQuery: function() {
        var self = this;
        return {
            type: 'count_unique',
            params: {
                event_collection: 'pageviews',
                interval: 'daily',
                target_property: 'anon.id'
            }
        };
    },
    _initDataviz: function() {
        var self = this;
        return self.super._initDataviz.call(self)
            .chartType('line')
            .dateFormat('%b %d')
            .chartOptions({
                tooltip: {
                    format: {
                        title: function(x) { return x.toDateString(); },
                        name: function() { return 'Visits'; }
                    }
                },
                axis: {
                    y: {
                        tick: {
                            format: self._helpers.hideNonIntegers,
                        }
                    },
                    x: {
                        tick: {
                            fit: false,
                        },
                    },
                },
            });
    },



});

// show most common referrers to this project from the last week
var ChartTopReferrers = oop.extend(UserFacingChart, {
    constructor: function(params) {
        this.super.constructor.call(this, params);
    },
    baseQuery: function() {
        var self = this;
        return {
            type: 'count_unique',
            params: {
                event_collection: 'pageviews',
                target_property: 'anon.id',
                group_by: 'referrer.info.domain'
            }
        };
    },
    _initDataviz: function() {
        var self = this;
        return self.super._initDataviz.call(self)
            .chartType('pie')
            .chartOptions({
                tooltip:{
                    format:{
                        name: function() { return 'Visits'; }
                    }
                },
            });
    },
    munger: function() {
        var self = this;
        var dataset = self.chart.dataset;
        dataset.sortRows('desc', function(row) {
            return row[1];
        });
        dataset.filterRows(function(row, index) {
            return index < self.MAX_DISPLAY_ENTRIES;
        });
        dataset.updateColumn(0, function(value, index, column) {
            return value === 'null' ? 'direct link' : value;
        });
    },
});


// The number of visits by hour across last week
var ChartVisitsServerTime = oop.extend(UserFacingChart, {
    constructor: function(params) {
        this.super.constructor.call(this, params);
    },
    baseQuery: function() {
        var self = this;
        return {
            type: 'count_unique',
            params: {
                event_collection: 'pageviews',
                target_property: 'anon.id',
                group_by: 'time.local.hour_of_day',
            }
        };
    },
    _initDataviz: function() {
        var self = this;
        return self.super._initDataviz.call(self)
            .chartType('bar')
            .chartOptions({
                tooltip:{
                    format:{
                        name: function() { return 'Visits'; }
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
                    y: {
                        tick: {
                            format: self._helpers.hideNonIntegers,
                        }
                    }
                },
            });
    },
    munger: function() {
        var self = this;
        var dataset = self.chart.dataset;
        // make sure all hours of the day 0-23 are present

        var foundHours = {};
        for (var i=dataset.matrix.length-1; i>0; i--) {
            var row = dataset.selectRow(i);
            foundHours[ row[0] ] = row[1];
            dataset.deleteRow(i);
        }

        for (var hour=0; hour<24; hour++) {
            var stringyNum = '' + hour;
            dataset.appendRow(stringyNum, [ foundHours[stringyNum] || 0 ]);
        }
    },
});

// most popular sub-pages of this project
var ChartPopularPages = oop.extend(UserFacingChart, {
    constructor: function(params) {
        var self = this;
        self.super.constructor.call(self, params);
        self.nodeTitle = params.nodeTitle || '';
    },
    baseQuery: function() {
        var self = this;
        return {
            type: 'count_unique',
            params: {
                event_collection: 'pageviews',
                target_property: 'anon.id',
                group_by: 'page.title'
            }
        };
    },
    _initDataviz: function() {
        var self = this;
        return self.super._initDataviz.call(self)
            .chartType('horizontal-bar')
            .chartOptions({
                tooltip:{
                    format:{
                        name: function() { return 'Visits'; }
                    }
                },
                axis: {
                    y: {
                        tick: {
                            format: self._helpers.hideNonIntegers,
                        }
                    }
                },
            });
    },
    munger: function() {
        var self = this;
        var dataset = self.chart.dataset;
        dataset.sortRows('asc', function(row) { return row[1]; });

        var nbrRows = dataset.matrix.length;
        var minimumIndex = nbrRows <= self.MAX_DISPLAY_ENTRIES ? 0 : nbrRows - self.MAX_DISPLAY_ENTRIES;
        dataset.filterRows(function(row, index) { return index >= minimumIndex; });

        dataset.updateColumn(0, function(value, index, column) {
            var title = value.replace(/^OSF \| /, '');
            // Strip off the project title, if present at beginning of string
            if (title.startsWith(self.nodeTitle)) {
                // strip off first N chars where N is project title length + 1 space
                var pageTitleIndex = self.nodeTitle.length + 1;
                title = title.slice(pageTitleIndex);
            }
            return title || 'Home';
        });
    },
});

module.exports = {
    UserFacingChart: UserFacingChart,
    ChartUniqueVisits: ChartUniqueVisits,
    ChartTopReferrers: ChartTopReferrers,
    ChartVisitsServerTime:ChartVisitsServerTime,
    ChartPopularPages: ChartPopularPages,
};
