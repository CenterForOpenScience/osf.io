'use strict';

var c3 = require('c3');
require('c3/c3.css');

var pikaday = require('pikaday');
require('pikaday-css');

var moment = require('moment');

var statistics = {};
$(document).ready(function() {

    var picker = new pikaday({
        field: document.getElementById('datepicker'),
        trigger: document.getElementById('datepicker-btn'),
        onSelect: function(){
            selectDate(picker.toString());
        }
    });

    loadPiwikData();

});

function statisticsSchema(nodeData, fileData){

    statistics.dates = nodeData['dates'];
    statistics.node = formatNodeData(nodeData['node']);
    statistics.children = formatChildrenData(nodeData['children']);
    statistics.files = formatFileData(fileData['files']);

}

function dataTypeToColumn(label, piwikType, piwikData) {
    var data = [label];

    for (var i=0; i < statistics['dates'].length; i++){
        var date = statistics['dates'][i];
        if($.isPlainObject(piwikData[date])) {
            data.push(piwikData[date][piwikType])
        } else {
            data.push(0)
        }
    }

    return data;
}

function formatNodeData(nodeData) {
    var data = {};

    var visits = dataTypeToColumn('Visits','nb_visits', nodeData[nodeId]);
    var uniqueVisitors = dataTypeToColumn('Unique Visitors','nb_uniq_visitors', nodeData[nodeId]);
    data[nodeId] = {
        visits : visits,
        uniqueVisitors: uniqueVisitors
    };

    return data;
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

function renderPiwikChart(stats, dataType){

    $('.piwikChart').height(200);

    var dates = statistics['dates'];
    dates.unshift('x');

    var chart = c3.generate({
        bindto: '.piwikChart',
        data: {
            x: 'x',
            columns: [
                dates,
                stats['node'][nodeId][dataType]
            ]
        },
        axis: {
            x: {
                type: 'timeseries',
                tick: {
                    format: '%b %d %Y',
                    culling: {
                        max: 5
                    }
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
        },
        legend: {
            show: false
        }
    });
}

function renderStatsTable(table, data, dataType){

    var table = $('#'+table);

    if(!$.isPlainObject(data)){
        table.append('<h4>This project has no public components for statistics.</h4>');
        return
    }

    table.append('<thead><th>Name</th><th> </th><th>' + dataType + '</th></thead>');

    for (var compGuid in data){

        var componentRow = $('<tr>');
        var total = 0;

        var compData = data[compGuid][dataType];
        for(var i=1; i < compData.length; i++){
            total += compData[i];
        }

        componentRow.append('<td>' + compGuid + '</td><td>Null</td><td>' + total + '</td>');
        table.append(componentRow);
    }

}

function selectDate(date){
    var endDate = moment(date);
    var startDate = moment(endDate).subtract(7, 'days');

    loadPiwikData()

}

function loadPiwikData(){

    $.when(
        $.get('http://localhost:7000/'+nodeId+'/nodeData', function(data){
        console.log(data);
    }),
        $.get('http://localhost:7000/fileData', {'files': nodeFiles})
    ).then(function(nodeData, fileData){
            statisticsSchema(nodeData[0], fileData[0]);
            renderPiwikChart(statistics, 'visits');
            renderStatsTable('componentStats', statistics['children'], 'visits');
            renderStatsTable('fileStats', statistics['files'], 'visits');
        },
        function(){
            console.log(arguments)
        }
    )

}
