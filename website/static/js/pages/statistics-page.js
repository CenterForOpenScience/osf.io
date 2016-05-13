'use strict';

//For keen.ready function
var keenAnalysis = require('keen-analysis');
var ProjectUsageStatistics = require('js/statistics');

keenAnalysis.ready(function(){
    new ProjectUsageStatistics();
});