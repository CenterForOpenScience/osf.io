'use strict';

var $  = require('jquery');
var Metrics = require('js/metrics/metrics');



$( document ).ready(function() {
    Metrics.UserGainMetrics();

    $('#institution-tab')[0].onclick = function() {
        Metrics.InstitutionMetrics();
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
