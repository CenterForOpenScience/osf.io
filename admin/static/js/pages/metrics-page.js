'use strict';

var $  = require('jquery');
var keenAnalysis = require('keen-analysis');
var Metrics = require('js/metrics/metrics');



keenAnalysis.ready(function() {

    Metrics.UserGainMetrics();

    $('#reload-node-logs')[0].onclick = function() {
        Metrics.NodeLogsPerUser();
    };

    $('#institution-tab')[0].onclick = function() {
        Metrics.InstitutionMetrics();
    };

    $('#active-user-tab')[0].onclick = function() {
        Metrics.ActiveUserMetrics();
    };

    $('#healthy-user-tab')[0].onclick = function() {
        Metrics.HealthyUserMetrics();
    };

    $('#raw-numbers-tab')[0].onclick = function() {
        Metrics.RawNumberMetrics();
    };
    $('#addons-tab')[0].onclick = function() {
        Metrics.AddonMetrics();
    };
    $('#preprints-tab')[0].onclick = function() {
        Metrics.PreprintMetrics();
    };
    $('#downloads-tab')[0].onclick = function() {
        Metrics.DownloadMetrics();
    };
    $('#preprints-range')[0].onclick = function() {
        var preprint_created = new keenAnalysis.Query('sum', {
            eventCollection: 'preprint_summary',
            targetProperty: 'provider.total',
            groupBy: ['provider.name'],
            interval: 'daily',
            timeframe: {
                'start': $('#start-date')[0].value,
                'end': $('#end-date')[0].value
            },
            timezone: "UTC"
        });

        Metrics.KeenRenderMetrics("#preprints-added", "line", preprint_created, 200);
    };
    $('#downloads-range')[0].onclick = function() {
        var download_count = new keenAnalysis.Query('sum', {
            eventCollection: 'download_count_summary',
            targetProperty: 'files.total',
            interval: 'daily',
            timeframe: {
                'start': $('#start-date-downloads')[0].value,
                'end': $('#end-date-downloads')[0].value
            },
            timezone: "UTC"
        });

        Metrics.KeenRenderMetrics("#download-counts", "line", download_count, 200);
    };

});
