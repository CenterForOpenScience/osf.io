'use strict';

require('keen-dataviz/dist/keen-dataviz.min.css');

var oop = require('js/oop');
var moment = require('moment');
var keenDataset = require('keen-dataset');
var keenDataviz = require('keen-dataviz');
var keenAnalysis = require('keen-analysis');


var UserFacingChart = oop.defclass({
    constructor: function(params) {
        var self = this;
        params = params || {};

        var required = ['keenProjectId', 'keenReadKey', 'containingElement'];
        required.forEach(function(paramName) {
            if (!params[paramName]) {
                throw new Error('Missing required argument "' + paramName + '"');
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

        // prebuild html for showing spinner
        var spinnerHtml = '';
        spinnerHtml += '<div class="ball-pulse ball-scale-blue text-center">';
        spinnerHtml += '    <div></div><div></div><div></div>';
        spinnerHtml += '</div>';
        self._spinnerHtml = spinnerHtml;
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
        throw new Error('Concrete class does not provide a "baseQuery" method!');
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
        // use moment to get local time offset.  Keen will divide daily intervals on midnight local
        // time, as calculated by the offset.  Passing Zulu time will cause days to always be
        // segmented on midnight UTC, regardless of user's local TZ.
        baseQuery.params.timeframe = {
            start: moment(self.startDate).format(),
            end: moment(self.endDate).format(),
        };
        return baseQuery;
    },

    /**
     * Builds underlying dataviz object, binds it to the containingElement.  Inheriting classes
     * should extend this method to set chart properties. Make sure to call the parent method!
     *
     * See: https://github.com/keen/keen-dataviz.js/tree/master/docs
     *
     * @method _initDataviz
     * @return {KeenDataviz}
     */
    _initDataviz: function() {
        var self = this;
        return new keenDataviz().el(self.containingElement);
    },

    /**
     * Processes the raw Keen response before passing to the chart.  If dataParser returns the raw
     * response or a similarly formatted Object, the chart will do its own parsing based on the type
     * of chart.  To bypass the charts default parsing, construct and return a KeenDataset object
     * here.
     *
     * See: https://github.com/keen/keen-dataviz.js/tree/master/docs/dataset
     * Default parsers:
     *   https://github.com/keen/keen-dataviz.js/blob/master/lib/dataset/utils/parsers.js
     *
     * @method dataParser
     * @return {Object} or {KeenDataviz}
     **/
    dataParser: function(resp) { return resp; },

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
     * Sets the date range over which the metric should apply, specifically the startDate and
     * endDate properties.
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

    // Fetch the DOM element the chart is rendered to.
    getElement: function() { return document.getElementById(this.containingElement.replace(/^#/, '')); },

    // Put up a COS spinner in the chart container.
    startSpinner: function() { this.getElement().innerHTML = this._spinnerHtml; },

    // Remove the COS spinner from the chart container.
    endSpinner: function() { this.getElement().innerHTML = ''; },

    /**
     * Show a spinner, issue the query to keen, then render the chart  If an error is returned, it
     * will be displayed within the chart element.
     *
     * @method buildChart
     * @return {null}
     */
    buildChart: function() {
        var self = this;
        if (!self.chart) {
            self.chart = self._initDataviz();
        }

        self.startSpinner();
        var query = self.query();
        self.keenClient
            .query(query.type, query.params)
            .then(function(res) {
                self.chart
                    .title(' ')
                    .data(self.dataParser(res))
                    .call(self.munger.bind(self));
                self.endSpinner();
                self.chart.render();
            })
            .catch(function(err) {
                self.endSpinner();
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
        self.nodeId = params.nodeId || '';
        self.titleForPath = {
            files: 'Files',
            analytics: 'Analytics',
            forks: 'Forks',
            registrations: 'Registrations',
            wiki: 'Wiki',
        };
    },
    baseQuery: function() {
        var self = this;
        return {
            type: 'count',
            params: {
                event_collection: 'pageviews',
                group_by: ['page.info.path', 'page.title'],
                filters: [
                    {
                        property_name: 'page.info.path',
                        operator: 'not_contains',
                        property_value: '/project/',
                    },
                ],

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

    // url path => page title is not 1:1, so we have to do our own aggregation
    dataParser: function(resp) {
        var self = this;
        var aggregatedResults = {};
        resp.result.forEach(function(result) {
            var path = result['page.info.path'];
            var pathParts = path.split('/');
            pathParts.shift(); // get rid of leading ""

            // if path begins with our node id: it's a project page.  Lookup the title using
            // the second part of the path. All wiki pages are consolidated under 'Wiki'.
            // If path begins with a guid-ish that is not the current node id, assume it's a
            // file and use the title provided.
            var pageTitle, pagePath;
            if (pathParts[0] === self.nodeId) {
                pageTitle = pathParts[1] ? self.titleForPath[pathParts[1]] : 'Home';
                pagePath = '/' + pathParts[0] + '/' + (pathParts[1] || '');
            }
            else if (/^\/[a-z0-9]{5}\/$/.test(path)) {
                pageTitle = 'File: ' + result['page.title'].replace(/^OSF \| /, '');
                pagePath = path;
            }

            // Didn't recognize the path, exclude the entry from the popular pages list.
            if (!pageTitle) {
                return;
            }

            if (!aggregatedResults[pagePath]) {
                aggregatedResults[pagePath] = {
                    path: pagePath,
                    result: 0,
                    title: pageTitle,
                };
            }
            aggregatedResults[pagePath].result += result.result;
            return;
        });

        var dataset = new keenDataset().type('double-grouped-metric');
        for (var path in aggregatedResults) {
            var result = aggregatedResults[path];
            dataset.set([ 'Result', result.title ], result.result);
        }
        return dataset;
    },
    munger: function() {
        var self = this;
        var dataset = self.chart.dataset;

        dataset.sortRows('asc', function(row) { return row[1]; });

        var nbrRows = dataset.matrix.length;
        var minimumIndex = nbrRows <= self.MAX_DISPLAY_ENTRIES ? 0 : nbrRows - self.MAX_DISPLAY_ENTRIES;
        dataset.filterRows(function(row, index) { return index >= minimumIndex; });

    },
});


module.exports = {
    UserFacingChart: UserFacingChart,
    ChartUniqueVisits: ChartUniqueVisits,
    ChartTopReferrers: ChartTopReferrers,
    ChartVisitsServerTime:ChartVisitsServerTime,
    ChartPopularPages: ChartPopularPages,
};
