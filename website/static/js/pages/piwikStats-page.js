'use strict';

var c3 = require('c3');
require('c3/c3.css');

var pikaday = require('pikaday');
require('pikaday-css');

var moment = require('moment');

var sparkline = require('jquery-sparkline');

var statisticsContext = {
    statistics: {},
    renderComponents: [],
    renderFiles: []
};

var currentPiwikParams = {
    method: 'VisitsSummary.get',
    period: 'day',
    date: 'last30',
    files: nodeFiles
};


$(document).ready(function() {

    var picker = new pikaday({
        field: document.getElementById('datepicker'),
        trigger: document.getElementById('datepickerButton'),
        onSelect: function(){
            selectDate(picker.toString());
        }
    });

    var startPicker = new pikaday({
        field: document.getElementById('startPicker'),
        maxDate: moment().toDate(),
        onSelect: function() {
            endPicker.setMinDate(moment(startPicker.toString()));
        }
    });

    var endPicker = new pikaday({
        field: document.getElementById('endPicker'),
        maxDate: moment().toDate(),
        onSelect: function(){
            selectRange(startPicker.toString(), endPicker.toString());
        }
    });

    $("li").on("click", function() {
        changeStats($(this).text());
    });

    initializeStats();

});

function getDataAndRender(){
     $.when(
        $.get('http://localhost:7000/'+nodeId+'/nodeData', currentPiwikParams),
        $.get('http://localhost:7000/fileData', currentPiwikParams)
    ).then(function(nodeData, fileData){
             statisticsSchema(nodeData[0], fileData[0]);
             renderStatistics();
        },
        function(){
            console.log(arguments)
        }
    )
}

function statisticsSchema(nodeData, fileData){

    statisticsContext.statistics.dates = nodeData['dates'];
    statisticsContext.statistics.node = formatData(nodeData['node']);
    statisticsContext.statistics.children = formatData(nodeData['children']);
    statisticsContext.statistics.files = formatData(fileData['files']);

    console.log(statisticsContext.statistics);

}

function dataTypeToColumn(dataType, piwikData) {
    var piwikType = getPiwikType(dataType);

    var data = [dataType];

    for (var i=0; i < statistics['dates'].length; i++){
        var date = statistics['dates'][i];

        //Debug
        var piwikStats = piwikData[date];
        if($.isPlainObject(piwikStats)) {
            data.push(piwikData[date][piwikType])
        } else {
            data.push(0)
        }
    }

    return data;
}

function formatData(piwikData) {

    if ($.isPlainObject(piwikData)){
        var data = {};
        var dataType = statistics['dataType'];

        for (var guid in piwikData){
            data[guid] = {};
            data[guid][dataType] = dataTypeToColumn(dataType, piwikData[guid]);
        }

        return data;
    }

    return [];
}

function formatChildrenData(childrenData) {

    if ($.isPlainObject(childrenData)){
        var children = {};

        for (var child in childrenData){
            children[child] = {
                visits: dataTypeToColumn('Visits', 'nb_visits', childrenData[child]),
                uniqueVisitors: dataTypeToColumn('Unique Visitors', 'nb_uniq_visitors', childrenData[child])
            }
        }

        return children;
    }

    return [];
}

function formatFileData(fileData) {

    if($.isPlainObject(fileData)){
        var files = {};

        for (var file in fileData){
            files[file] = {
                visits: dataTypeToColumn('Visits', 'nb_visits', fileData[file]),
                uniqueVisitors: dataTypeToColumn('Unique Visitors', 'nb_uniq_visitors', fileData[file])
            }
        }

        return files;
    }

    return [];
}

function initializeStats(){
    statistics['dataType'] = "Visits";
    getDataAndRender();
}

function renderPiwikChart(stats, dataType){

    $('.piwikChart').height(300);

    var dates = statistics['dates'];
    dates.unshift('x');

    var data = stats['node'][nodeId][dataType];

    var chart = c3.generate({
        bindto: '.piwikChart',
        data: {
            x: 'x',
            columns: [
                dates,
                data
            ]
        },
        axis: {
            x: {
                type: 'timeseries',
                tick: {
                    format: '%b %d %Y',
                    culling: {
                        max: 5
                    },
                    rotate: 60
                },
                padding: {
                    left: 0
                }
            },
            y: {
                padding: {
                    bottom: 0
                }
            }
        },
        padding: {
            right: 50,
            bottom: 20
        }
    });

    data.shift();

    if(d3.max(data) < 10){
        chart.axis.max({y: 10});
    }

}

function renderStatsTable(table, data, dataType){

    var table = $('#'+table);

    if(!$.isPlainObject(data)){
        table.append('<h4>This project has no public components for statistics.</h4>');
        return
    }

    table.append('<thead><th class="col-md-6">Name</th><th class="col-md-3">' + dataType + '</th><th id="sparkCell" class="col-md-3">Over Time</th></thead>');

    for (var compGuid in data){

        var componentRow = $('<tr>');
        var total = 0;

        var compData = data[compGuid][dataType];
        var sparkData = [];
        for(var i=1; i < compData.length; i++){
            total += compData[i];
            sparkData.push(compData[i]);
        }

        componentRow.append('<td>' + compGuid + '</td><td>' + total + '</td><td class="inlinesparkline">' + sparkData.toString() + '</td>');
        table.append(componentRow);
    }

}

function selectDate(date) {
    var endDate = moment(date);
    var startDate = moment(endDate).subtract(7, 'days');

    var date = startDate.format('YYYY-MM-DD') + ',' + endDate.format('YYYY-MM-DD');

    currentPiwikParams['date'] = date;
    updateStatistics();

}

function selectRange(start, end){
    var startDate = moment(start);
    var endDate = moment(end);
    var startCheck = moment(endDate).subtract(7,'days');

    if (endDate.isBefore(startDate)){
        return;
    }
    var dateRange;
    if (startCheck.isBefore(startDate)){
        dateRange = startCheck.format('YYYY-MM-DD') + ',' + endDate.format('YYYY-MM-DD');
    } else {
        dateRange = startDate.format('YYYY-MM-DD') + ',' + endDate.format('YYYY-MM-DD');
    }

    currentPiwikParams['date'] = dateRange;
    updateStatistics();
}

function updateStatistics() {

    $('.piwikChart').empty();
    $('#componentStats').empty();
    $('#fileStats').empty();

    getDataAndRender();

}

function renderStatistics() {
    var dataType = statistics['dataType'];
    renderPiwikChart(statistics, dataType);
    renderStatsTable('componentStats', statistics['children'], dataType);
    renderStatsTable('fileStats', statistics['files'], dataType);
    //$('.inlinesparkline').sparkline('html',
    //    {
    //        lineColor: '#204762',
    //        fillColor: '#EEEEEE',
    //        spotColor: '#337ab7',
    //        defaultPixelsPerValue: Math.max(Math.floor($('#sparkCell').width() / statistics['dates'].length), 2)
    //    });
}

function getMethodFromType(dataType){
    if (dataType == "Page Views" || dataType == "Unique Page Views"){
        return "Actions.get"
    }
    return "VisitsSummary.get"
}

function getPiwikType(dataType) {
    switch (dataType){
        case "Visits":
            return "nb_visits";

        case "Unique Visitors":
            return "nb_uniq_visitors";

        case "Page Views":
            return "nb_pageviews";

        case "Unique Page Views":
            return "nb_uniq_pageviews";
    }
}

function changeStats(dataType){
    var method = getMethodFromType(dataType);
    var piwikType = getPiwikType(dataType);
    currentPiwikParams['method'] = method;
    statistics['dataType'] = dataType;

    updateStatistics();

}


