/*global describe, it, expect, example, before, after, beforeEach, afterEach, mocha, sinon*/
'use strict';

var assert = require('chai').assert;
var $osf = require('js/osfHelpers');

var Stats = require('js/share/stats');

describe('share/stats', () => {

    describe('#sourcesAgg', () => {

        it('builds correct query, aggregation and filters for a source aggregation', () => {
            var returnedAgg = Stats.sourcesAgg;
            var requiredAgg = {
                'query': {
                  'match_all': {}
                },
                'aggregations': {
                  'sources': {
                    'terms': {
                      'field': '_type',
                      'size': 0,
                      'exclude': 'of|and|or',
                      'min_doc_count': 0
                    }
                  }
                }
              };
            assert.deepEqual(returnedAgg, requiredAgg);
        });
    });

    describe('#sourcesByDatesAgg', () => {

        it('builds correct query, aggregation and filters for a sourcesByDates aggregation', () => {
            var returnedAgg = Stats.sourcesByDatesAgg();
            var requiredAgg = {
                'aggregations': {
                  'sourcesByTimes': {
                    'terms': {
                      'field': '_type',
                      'size': 0,
                      'exclude': 'of|and|or',
                      'min_doc_count': 0
                    },
                    'aggregations': {
                      'articlesOverTime': {
                          'aggregations': {
                              'articlesOverTime': {
                                'date_histogram': {
                                    'field': 'providerUpdatedDateTime',
                                    'interval': 'week',
                                    'min_doc_count': 0,
                                    'extended_bounds': {
                                        'min': 1429562338929,
                                        'max': 1437424738929
                                    }
                                }
                              }
                            },
                            'filter': {
                                'range': {
                                    'providerUpdatedDateTime': {
                                        'gte': 1429562338929,
                                        'lte': 1437424738929
                                    }
                                }
                            }
                        }
                    }
                  }
                },
            };


            requiredAgg.aggregations.sourcesByTimes.aggregations.articlesOverTime.aggregations.articlesOverTime.date_histogram.extended_bounds = returnedAgg.aggregations.sourcesByTimes.aggregations.articlesOverTime.aggregations.articlesOverTime.date_histogram.extended_bounds;
            requiredAgg.aggregations.sourcesByTimes.aggregations.articlesOverTime.filter.range.providerUpdatedDateTime = returnedAgg.aggregations.sourcesByTimes.aggregations.articlesOverTime.filter.range.providerUpdatedDateTime ;
            var diffInMs = returnedAgg.aggregations.sourcesByTimes.aggregations.articlesOverTime.aggregations.articlesOverTime.date_histogram.extended_bounds.max - returnedAgg.aggregations.sourcesByTimes.aggregations.articlesOverTime.aggregations.articlesOverTime.date_histogram.extended_bounds.min;
            var testDate = new Date(0);
            testDate.setUTCSeconds(diffInMs/1000);
            assert.equal(testDate.getMonth(),3);
            assert.deepEqual(returnedAgg, requiredAgg);
        });
    });

    describe('#shareDonutGraphParser', () => {

        it('Parse returned sources elasticsearch data into correct format for c3 donut graph, including correct colors', () => {
            var rawData = {};
            rawData.aggregations = {'sources':{
                'buckets':[
                  { 'key': 'figshare','doc_count': 1378},
                  { 'key': 'calhoun', 'doc_count': 119},
                  { 'key': 'ucescholarship', 'doc_count': 74},
                  { 'key': 'mit', 'doc_count': 68},
                  { 'key': 'pubmedcentral', 'doc_count': 52 },
                  { 'key': 'datacite', 'doc_count': 40 },
                  { 'key': 'dash', 'doc_count': 28},
                  { 'key': 'caltech', 'doc_count': 24},
                  { 'key': 'bhl', 'doc_count': 23},
                  { 'key': 'scholarworks_umass', 'doc_count': 23},
                  { 'key': 'udel', 'doc_count': 20},
                  { 'key': 'upennsylvania', 'doc_count': 13},
                  { 'key': 'doepages','doc_count': 12},
                  { 'key': 'smithsonian', 'doc_count': 8},
                  { 'key': 'opensiuc', 'doc_count': 4},
                  { 'key': 'scholarsbank', 'doc_count': 4},
                  { 'key': 'trinity', 'doc_count': 2},
                  { 'key': 'asu', 'doc_count': 1}],
                'sum_other_doc_count': 0,
                'doc_count_error_upper_bound': 0
              }
            };
            var returnedData = Stats.shareDonutGraphParser(rawData);
            var requiredData = {
                  'name': 'shareDonutGraph',
                  'columns': [
                    [ 'figshare',1378],
                    ['calhoun',119],
                    ['ucescholarship',74],
                    ['mit',68],
                    ['pubmedcentral',52],
                    ['datacite',40],
                    ['dash',28],
                    ['caltech',24],
                    ['bhl',23],
                    ['scholarworks_umass',23],
                    ['udel',20],
                    ['upennsylvania',13],
                    ['doepages',12],
                    ['smithsonian',8],
                    ['opensiuc',4],
                    ['scholarsbank',4],
                    ['trinity',2],
                    ['asu',1]
                  ],
                  'colors': {
                    'figshare': '#a6cee3',
                    'calhoun': '#1f78b4',
                    'ucescholarship': '#b2df8a',
                    'mit': '#33a02c',
                    'pubmedcentral': '#fb9a99',
                    'datacite': '#e31a1c',
                    'dash': '#fdbf6f',
                    'caltech': '#ff7f00',
                    'bhl': '#cab2d6',
                    'scholarworks_umass': '#6a3d9a',
                    'udel': '#ffff99',
                    'upennsylvania': '#b15928',
                    'doepages': '#62a3cb',
                    'smithsonian': '#68ab9f',
                    'opensiuc': '#72bf5b',
                    'scholarsbank': '#979d62',
                    'trinity': '#ef5a5a',
                    'asu': '#f06c45'
                  },
                  'type': 'donut',
                  'title': '18 Providers'
                };
            assert.deepEqual(returnedData, requiredData);
        });
    });

    describe('#shareTimeGraphParser', () => {

        it('Parse returned sources elasticsearch data into correct format for c3 stacked graph, including correct colors', () => {
            var rawData = {};
            rawData.aggregations = {
              'sourcesByTimes': {
                'buckets': [
                  {
                    'articlesOverTime': {
                        'articlesOverTime': {
                            'buckets': [
                                {'key': 1434326400000, 'doc_count': 0},
                                {'key': 1434931200000, 'doc_count': 0},
                                {'key': 1435536000000, 'doc_count': 1378},
                                {'key': 1436140800000, 'doc_count': 0},
                                {'key': 1436745600000, 'doc_count': 0},
                                {'key': 1437350400000, 'doc_count': 0}
                            ]
                        }
                    },
                    'key': 'figshare',
                    'doc_count': 1378
                  },
                  {
                    'articlesOverTime': {
                        'articlesOverTime': {
                            'buckets': [
                                {'key': 1434326400000, 'doc_count': 0},
                                {'key': 1434931200000, 'doc_count': 0},
                                {'key': 1435536000000, 'doc_count': 73},
                                {'key': 1436140800000, 'doc_count': 0},
                                {'key': 1436745600000, 'doc_count': 0},
                                {'key': 1437350400000, 'doc_count': 0}
                            ]
                        }
                    },
                    'key': 'ucescholarship',
                    'doc_count': 73
                  }
                ],
                'sum_other_doc_count': 390,
                'doc_count_error_upper_bound': 20
              }
            };
            var returnedData = Stats.shareTimeGraphParser(rawData);
            var requiredData = {
              'name': 'shareTimeGraph',
              'columns': [
                ['x', 1434326400000, 1434931200000, 1435536000000, 1436140800000, 1436745600000, 1437350400000],
                ['figshare', 0, 0, 1378, 1378, 1378, 1378],
                ['ucescholarship', 0, 0, 73, 73, 73, 73]
              ],
              'colors': {
                'figshare': '#a6cee3',
                'ucescholarship': '#1f78b4'
              },
              'type': 'area-spline',
              'x': 'x',
              'groups': [['x','figshare', 'ucescholarship']]
            };
            assert.deepEqual(returnedData, requiredData);
        });
    });
});


