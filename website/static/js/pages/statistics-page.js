'use strict';

require('pikaday-css');

var $  = require('jquery');
var pikaday = require('pikaday');
var Cookie = require('js-cookie');
var keenAnalysis = require('keen-analysis');
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
        projectUsageStats.visitsByDay('#visits', startDate, endDate);
        projectUsageStats.topReferrers('#topReferrers', startDate, endDate);
        projectUsageStats.popularPages('#popularPages', startDate, endDate, window.contextVars.node.title);
        projectUsageStats.visitsServerTime('#serverTimeVisits', startDate, endDate);
    }

    function updateStartDate() {
        startPicker.setStartRange(startDate);
        endPicker.setStartRange(startDate);
        endPicker.setMinDate(startDate);
    }

    function updateEndDate() {
        startPicker.setEndRange(endDate);
        startPicker.setMaxDate(endDate);
        endPicker.setEndRange(endDate);
    }

    var oneDayInMs = 24 * 60 * 60 * 1000;
    var thirtyDaysAgoInMs = 30 * oneDayInMs;
    var statsMinDate = new Date(2013, 5, 1);
    var statsMaxDate = new Date();

    var startDate = new Date(Date.now() - thirtyDaysAgoInMs);
    var startPickerElem = document.getElementById('startDatePicker');
    var startPicker = new pikaday(
        {
            bound: true,
            field: startPickerElem,
            defaultDate: startDate,
            setDefaultDate: true,
            minDate: statsMinDate,
            maxDate: statsMaxDate,
            onSelect: function() {
                startDate = this.getDate();
                updateStartDate();
                startPickerElem.value = this.toString();
            }
        }
    );

    var endPickerElem = document.getElementById('endDatePicker');
    var endDate = new Date(Date.now() - oneDayInMs);
    var endPicker = new pikaday(
        {
            bound: true,
            field: endPickerElem,
            defaultDate: endDate,
            setDefaultDate: true,
            minDate: statsMinDate,
            maxDate: statsMaxDate,
            onSelect: function() {
                endDate = this.getDate();
                updateEndDate();
                endPickerElem.value = this.toString();
            }
        }
    );


    updateStartDate();
    updateEndDate();

    var projectUsageStats = new ProjectUsageStatistics(
        window.contextVars.keen.public.projectId,
        window.contextVars.keen.public.readKey
    );
    drawAllCharts(startDate, endDate);

    $('#updateStatsDates').on('submit', function() {
        drawAllCharts(startDate, endDate);
        return false;
    });

});
