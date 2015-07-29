'use strict';

var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
//This module contains a bunch of generic charts and parsers for formating the correct data for them

var COLORBREWER_COLORS = [[166, 206, 227], [31, 120, 180], [178, 223, 138], [51, 160, 44], [251, 154, 153], [227, 26, 28], [253, 191, 111], [255, 127, 0], [202, 178, 214], [106, 61, 154], [255, 255, 153], [177, 89, 40]]
var charts = {};

function calculateDistanceBetweenColors(color1, color2) {
    return [Math.floor((color1[0] + color2[0]) / 2),
            Math.floor((color1[1] + color2[1]) / 2),
            Math.floor((color1[2] + color2[2]) / 2)];
}

function rgbToHex(rgb) {
    var rgb = rgb[2] + (rgb[1] << 8) + (rgb[0] << 16);
    return  '#' + (0x1000000 + rgb).toString(16).substring(1);
}

function timeSinceEpochInMsToMMYY(timeSinceEpochInMs) {
    var d = new Date(0);
    d.setUTCSeconds(timeSinceEpochInMs / 1000);
    return d.getMonth().toString() + '/' + d.getFullYear().toString().substring(2);
}

charts.donutChart = function (data, name, callback) {
    if (callback){data.onclick = callback.onclick; }
    data.type = 'donut';
    return c3.generate({
        bindto: '#' + name,
        size: {
            height: 200
        },
        data: data,
        donut: {
            title: data.title,
            label: {
                format: function (ratio) {
                    return Math.round(ratio * 100) + '%';
                }
            }
        },
        legend: {
            show: false
        }
    });
};

charts.timeseriesChart = function (data, name, callback) { //TODO this should be made dumber, data need only be the data for this graph, not all...
    data.type = 'area-spline';
    return c3.generate({
        bindto: '#' + name,
        size: {
            height: 250
        },
        data: data,
        subchart: { //TODO @bdyetton fix the aggregation that the subchart pulls from so it always has the global range results
            show: true,
            size: {
                height: 30
            },
            onbrush: callback ? callback.onbrush : undefined
        },
        axis: {
            x: {
                type: 'timeseries',
                tick: {
                    format: function (d) {return timeSinceEpochInMsToMMYY(d); }
                }
            },
            y: {
                label: {
                    text: 'Number of Events',
                    position: 'outer-middle'
                },
                tick: {
                    count: 8,
                    format: function (d) {return parseInt(d).toFixed(0); }
                }
            }
        },
        legend: {
            show: false
        },
        tooltip: {
            grouped: false
        }
    });
};

//Parsers
charts.singleLevelAggParser = function (data, levelNames) {
    var chartData = {};
    chartData.name = levelNames[0];
    chartData.columns = [];
    chartData.colors = {};
    chartData.type = 'donut';
    var providerCount = 0;
    var hexColors = charts.generateColors(data.aggregations[levelNames[0]].buckets.length);
    var i = 0;
    data.aggregations[levelNames[0]].buckets.forEach(
        function (bucket) {
            chartData.columns.push([bucket.key, bucket.doc_count]);
            providerCount = providerCount + (bucket.doc_count ? 1 : 0); //TODO @bdyetton generalise this...
            chartData.colors[bucket.key] = hexColors[i];
            i = i + 1;
        }
    );
    chartData.title = providerCount.toString() + ' Provider' + (providerCount !== 1 ? 's' : '');
    $('.c3-chart-arcs-title').text(chartData.title); //dynamically update chart title
    return chartData;
};

charts.twoLevelAggParser = function (data, levelNames) {
    var chartData = {};
    chartData.name = levelNames[0];
    chartData.columns = [];
    chartData.colors = {};
    chartData.x = 'x';
    chartData.groups = [];
    var grouping = [];
    grouping.push('x');
    var hexColors = charts.generateColors(data.aggregations[levelNames[0]].buckets.length);
    var i = 0;
    var xCol = [];
    data.aggregations[levelNames[0]].buckets.forEach(
        function (levelTwoItem) {
            chartData.colors[levelTwoItem.key] = hexColors[i];
            var column = [levelTwoItem.key];
            grouping.push(levelTwoItem.key);
            levelTwoItem[levelNames[1]].buckets.forEach(function(date){
                column.push(date.doc_count);
                if (i === 0) {
                    xCol.push(date.key);
                }
            });
            chartData.columns.push(column);
            i = i + 1;
        }
    );
    chartData.groups.push(grouping);
    xCol.unshift('x');
    chartData.columns.unshift(xCol);
    return chartData;
};

charts.generateColors = function(numColors) {
    var colorsToGenerate = COLORBREWER_COLORS.slice();
    var colorsUsed = [];
    var colorsOut = [];
    var colorsNorm = [];

    while (colorsOut.length < numColors) {
        var color = colorsToGenerate.shift();
        if (typeof color === 'undefined'){
            colorsToGenerate = charts.getNewColors(colorsUsed);
            colorsUsed = [];
        } else {
            colorsUsed.push(color);
            colorsNorm.push(color);
            colorsOut.push(rgbToHex(color));
        }
    }
    return colorsOut;
};

charts.getNewColors = function(colorsUsed) {
    var newColors = [];
    for (var i=0; i < colorsUsed.length-1; i++) {
        newColors.push(calculateDistanceBetweenColors(colorsUsed[i], colorsUsed[i + 1]));
    }
    return newColors;
};

module.exports = charts;
