'use strict';

var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var widgetUtils = require('js/search_dashboard/widgetUtils');

require('c3/c3.css');
require('../../css/search_widget.css');

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

/**
 * Wraps and returns a c3 chart in a component
 * Only creates new component when an update to this widget has been requested
 *
 * @param {Object} c3ChartSetup: A fully setup c3 chart object
 * @param {Object} vm: vm of the searchDashboard
 * @param {Object} divID: id of the chart (name of widget)
 * @return {m.component object}  c3 chart wrapped in component
 */
charts.c3componetize = function(c3ChartSetup, vm, divID) {
    return m('div.c3-chart-padding', {id: divID,
                    config: function(element, isInit, context){
                        if (!widgetUtils.updateTriggered(divID,vm)) {return; }
                        return c3.generate(c3ChartSetup);
                    }
            });
};

/**
 * Creates a c3 donut chart component
 *
 * @param {Object} rawData: Data to populate chart after parsing raw data
 * @param {Object} vm: vm of the searchDashboard
 * @param {Object} widget: params of the widget that chart is being created for
 * @return {m.component object}  c3 chart wrapped in component
 */
charts.donutChart = function (rawData, vm, widget) {
    var data = charts.singleLevelAggParser(rawData, widget.levelNames);
    data.onclick = widget.displayArgs.callback.onclick ? widget.displayArgs.callback.onclick.bind({
        vm: vm,
        widget: widget
    }) : undefined;
    data.type = 'donut';

    var chartSetup = {
        bindto: '#' + widget.levelNames[0],
        size: {
            height: widget.size[1]
        },
        data: data,
        donut: {
            title: data.title,
            label: {
                format: function (value, ratio, id) {
                    return Math.round(ratio * 100) + '%';
                }
            }
        },
        legend: {
            show: false
        }
    };
    return charts.c3componetize(chartSetup,vm, widget.levelNames[0]);
};

/**
 * Creates a c3 timeseries chart component after parsing raw data
 *
 * @param {Object} rawData: Data to populate chart
 * @param {Object} vm: vm of the searchDashboard
 * @param {Object} widget: params of the widget that chart is being created for
 * @return {m.component object}  c3 chart wrapped in component
 */
charts.timeseriesChart = function (rawData, vm, widget) {
    var data = charts.twoLevelAggParser(rawData, widget.levelNames);
    data.type = 'area-spline';
    var chartSetup = {
        bindto: '#' + widget.levelNames[0],
        size: {
            height: widget.size[1]
        },
        data: data,
        //TODO @bdyetton fix the aggregation that the subchart pulls from so it always has the global range results
        subchart: {
            show: true,
            size: {
                height: 30
            },
            onbrush: widget.displayArgs.callback ? widget.callback.displayArgs.onbrush.bind({vm: vm, widget: widget}) : undefined
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
    };
    return charts.c3componetize(chartSetup, vm, widget.levelNames[0]);
};

/**
 * Parses a single level of elastic search data for a c3 single level chart (such as a donut)
 *
 * @param {Object} data: raw elastic aggregation Data to parse
 * @param {Object} levelNames: names of each level (one in this case)
 * @return {m.component object}  parsed data
 */
charts.singleLevelAggParser = function (data, levelNames) {
    var chartData = {};
    chartData.name = levelNames[0];
    chartData.columns = [];
    chartData.colors = {};
    chartData.type = 'donut';
    var count = 0;
    var hexColors = charts.generateColors(data.aggregations[levelNames[0]].buckets.length);
    var i = 0;
    data.aggregations[levelNames[0]].buckets.forEach(
        function (bucket) {
            console.log(bucket.key);
            chartData.columns.push([bucket.key, bucket.doc_count]);
            count = count + (bucket.doc_count ? 1 : 0);
            chartData.colors[bucket.key] = hexColors[i];
            i = i + 1;
        }
    );
    chartData.title = count.toString() + ' ' + (count !== 1 ? levelNames[0] : levelNames[0].slice(0,-1));
    $('.c3-chart-arcs-title').text(chartData.title); //dynamically update chart title
    return chartData;
};

/**
 * Parses a single level of elastic search data for a c3 two level chart (such as a timeseries or histogram)
 *
 * @param {Object} data: raw elastic aggregation Data to parse
 * @param {Object} levelNames: names of each level (two in this case)
 * @return {m.component object}  parsed data
 */
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

/**
 * Returns a requested number of unique complementary colors
 *
 * @param {integer} numColors: number of colors to return
 * @return {array}  Array of Hex color values
 */
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

/**
 * Returns a colors in the middle of current colors
 *
 * @param {array} colorsUsed: colors used
 * @return {array}  new colors to use
 */
charts.getNewColors = function(colorsUsed) {
    var newColors = [];
    for (var i=0; i < colorsUsed.length-1; i++) {
        newColors.push(calculateDistanceBetweenColors(colorsUsed[i], colorsUsed[i + 1]));
    }
    return newColors;
};

module.exports = charts;
