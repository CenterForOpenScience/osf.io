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

});
