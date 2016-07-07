'use strict';

var $  = require('jquery');
var Cookie = require('js-cookie');
var keenAnalysis = require('keen-analysis');
var DateRangePicker = require('js/dateRangePicker');
var ProjectUsageStatistics = require('js/statistics');

$(function(){
    // Make adblock message permanently dismissible
    var adBlockPersistKey = 'adBlockDismiss';
    var $adBlock = $('#adBlock').on('closed.bs.alert', function() {
        Cookie.set(adBlockPersistKey, '1', {path: '/'});
    });
    var dismissed = Cookie.get(adBlockPersistKey) === '1';
    if (!dismissed) {
        $adBlock.show();
    }
});




keenAnalysis.ready(function(){
    function drawAllCharts(statsStartDate, statsEndDate) {
        projectUsageStats.visitsByDay('#visits', statsStartDate, statsEndDate);
        projectUsageStats.topReferrers('#topReferrers', statsStartDate, statsEndDate);
        projectUsageStats.visitsServerTime('#serverTimeVisits', statsStartDate, statsEndDate);
        projectUsageStats.popularPages(
            '#popularPages', statsStartDate, statsEndDate,
            window.contextVars.node.title
        );
    }

    var oneDayInMs = 24 * 60 * 60 * 1000;
    var thirtyDaysAgoInMs = 30 * oneDayInMs;

    var statsMinDate = new Date(2013, 5, 1);
    var statsMaxDate = new Date();

    var startPickerElem = document.getElementById('startDatePicker');
    var startDate = new Date(Date.now() - thirtyDaysAgoInMs);

    var endPickerElem = document.getElementById('endDatePicker');
    var endDate = new Date(Date.now() - oneDayInMs);

    var dateRangePicker = new DateRangePicker(
        startPickerElem, startDate,
        endPickerElem, endDate,
        statsMinDate, statsMaxDate
    );

    var projectUsageStats = new ProjectUsageStatistics(
        window.contextVars.keen.public.projectId,
        window.contextVars.keen.public.readKey
    );
    drawAllCharts(dateRangePicker.startDate, dateRangePicker.endDate);

    $('#updateStatsDates').on('submit', function() {
        drawAllCharts(dateRangePicker.startDate, dateRangePicker.endDate);
        return false;
    });

});
