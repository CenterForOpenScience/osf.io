'use strict';

var $  = require('jquery');
var keenAnalysis = require('keen-analysis');
var Metrics = require('js/metrics/metrics-mw');



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
        Metrics.RenderPreprintMetrics({
            start: $('#start-date')[0].value,
            end: $('#end-date')[0].value
        });
    };
    $('#downloads-range')[0].onclick = function() {
        Metrics.RenderDownloadMetrics({
            start: $('#start-date-downloads')[0].value,
            end: $('#end-date-downloads')[0].value
        });
    };

});
