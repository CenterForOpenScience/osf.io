'use strict';
var c3 = require('c3');
require('c3/c3.css');

var statistics = {};

$(document).ready(function() {

    $.when(
        $.get('http://localhost:6969/'+nodeId+'/nodeData', function (data) {
            return data;
        }),

        $.get('http://localhost:6969/fileData', {'files': nodeFiles}, function(data) {
            return data;
        })
    ).then(function(nodeData, fileData){
            statisticsSchema(nodeData[0], fileData[0]);
            renderPiwikChart(statistics, 'visits');
        },
        function(){
            console.log(arguments)
        }
    )
});

function statisticsSchema(nodeData, fileData){

    statistics = {
        node: formatNodeData(nodeData['node']),
        children: formatChildrenData(nodeData['children']),
        files: formatFileData(fileData['files'])
    };

}

function extractDataType(piwikType, piwikData) {
    var data = [];

    for (var date in piwikData){
        if($.isPlainObject(piwikData[date])) {
            data.push({date: date, data: piwikData[date][piwikType]})
        } else {
            data.push({date: date, data: 0})
        }
    }

    return data;
}

function formatNodeData(nodeData) {
    var node = {};

    var visits = extractDataType('nb_visits', nodeData[nodeId]);
    var uniqueVisitors = extractDataType('nb_uniq_visitors', nodeData[nodeId]);

    node[nodeId] = {
        visits: visits,
        uniqueVisitors: uniqueVisitors
    };

    return node
}

function formatChildrenData(childrenData) {

    if ($.isPlainObject(childrenData)){
        var children = {};

        for (var child in childrenData){
            children[child] = {
                visits: extractDataType('nb_visits', childrenData[child]),
                uniqueVisitors: extractDataType('nb_uniq_visitors', childrenData[child])
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
                visits: extractDataType('nb_visits', fileData[file]),
                uniqueVisitors: extractDataType('nb_uniq_visitors', fileData[file])
            }
        }

        return files;
    }

    return [];
}

function renderPiwikChart(dataSchema, dataType){

    $('.piwikChart').height(200);

    var chart = c3.generate({
        bindto: '.piwikChart',
        data: {
            json: dataSchema['node'][nodeId][dataType],
            keys: {
                x: 'date',
                value: ['data']
            }
        },
        axis: {
            x: {
                type: 'timeseries',
                tick: {
                    format: '%Y-%m-%d'
                }
            }
        }
    });
}

