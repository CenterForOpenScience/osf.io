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
    function updateDateRangeDisplay(statsStartDate, statsEndDate) {
        $('#startDateString').removeClass('ball-pulse ball-pulse-small ball-scale-blue').text(statsStartDate.toLocaleDateString());
        $('#endDateString').removeClass('ball-pulse ball-pulse-small ball-scale-blue').text(statsEndDate.toLocaleDateString());
    }

    function toggleDateRangePickerView() {
        $('#dateRange').toggleClass('hidden');
        $('#dateRangeForm').toggleClass('hidden');
    }

    function drawAllCharts(allCharts, statsStartDate, statsEndDate) {
        allCharts.forEach(function(chart) {
            chart.setDateRange(statsStartDate, statsEndDate);
            chart.buildChart();
        });
    }

    var oneDayInMs = 24 * 60 * 60 * 1000;
    var thirtyDaysAgoInMs = 30 * oneDayInMs;
    var startDate = new Date(Date.now() - thirtyDaysAgoInMs);
    var endDate = new Date(Date.now());

    updateDateRangeDisplay(startDate, endDate);

    var dateRangePicker = new DateRangePicker({
        startPickerElem: document.getElementById('startDatePicker'),
        startDate: startDate,
        endPickerElem: document.getElementById('endDatePicker'),
        endDate: endDate,
        minDate: new Date(2013, 5, 1),
        maxDate: new Date(),
    });

    var authParams = {
        keenProjectId: window.contextVars.keen.public.projectId,
        keenReadKey: window.contextVars.keen.public.readKey,
    };

    var allCharts = [
        new ProjectUsageStatistics.ChartUniqueVisits(
            $.extend({}, authParams, {containingElement: '#visits'})
        ),
        new ProjectUsageStatistics.ChartTopReferrers(
            $.extend({}, authParams, {containingElement: '#topReferrers'})
        ),
        new ProjectUsageStatistics.ChartVisitsServerTime(
            $.extend({}, authParams, {containingElement: '#serverTimeVisits'})
        ),
        new ProjectUsageStatistics.ChartPopularPages(
            $.extend({}, authParams, {
                containingElement: '#popularPages',
                nodeId: window.contextVars.node.id,
            })
        ),
    ];

    drawAllCharts(allCharts, dateRangePicker.startDate, dateRangePicker.endDate);

    $('#showDateRangeForm').on('click', function() { toggleDateRangePickerView(); });

    $('#dateRangeForm').on('submit', function() {
        updateDateRangeDisplay(dateRangePicker.startDate, dateRangePicker.endDate);
        toggleDateRangePickerView();
        drawAllCharts(allCharts, dateRangePicker.startDate, dateRangePicker.endDate);
        return false;
    });

});
