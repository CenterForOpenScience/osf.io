'use strict';

var c3 = require('c3');
var m = require('mithril');
var $ = require('jquery');
var widgetUtils = require('js/search_dashboard/widgetUtils');

require('c3/c3.css');
require('./css/search-widget.css');

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

/**
 * Returns a colors in the middle of current colors
 *
 * @param {Array} colorsUsed: colors used
 * @return {Array}  new colors to use
 */
function getNewColors (colorsUsed) {
    var newColors = [];
    for (var i=0; i < colorsUsed.length-1; i++) {
        newColors.push(calculateDistanceBetweenColors(colorsUsed[i], colorsUsed[i + 1]));
    }
    return newColors;
};

/**
 * Returns a requested number of unique complementary colors
 *
 * @param {integer} numColors: number of colors to return
 * @return {Array}  Array of Hex color values
 */
charts.generateColors = function(numColors) {
    var colorsToGenerate = COLORBREWER_COLORS.slice();
    var colorsUsed = [];
    var colorsOut = [];

    while (colorsOut.length < numColors) {
        var color = colorsToGenerate.shift();
        if (typeof color === 'undefined'){
            colorsToGenerate = getNewColors(colorsUsed);
            colorsUsed = [];
        } else {
            colorsUsed.push(color);
            colorsOut.push(rgbToHex(color));
        }
    }
    return colorsOut;
};

/**
 * Finds the first range filter and applies its bounds to the timegraphs zoom.
 * This is useful when instantiating a page from URL
 *
 * @param {Object} request: The request to get filter bounds from
 * @return {Array}  Zoom bounds in int format (time since epoch in MS)
 */
charts.getZoomFromTimeRangeFilter = function(request){
    var zoom = null;
    request.userDefinedANDFilters.some(function(filterString) {
        var filterParts = filterString.split('='); //remove lock qualifier if it exists
        if (filterParts[1] !== undefined) {return; } //there is a lock, so do nothing with this filter

        var parts = filterParts[0].split(':');
        var type = parts[0];
        if (type === 'range') { //TODO this assumes all range filters work on dates, better would be to check if field matches the 'date_created'
            zoom = [parseInt(parts[2]), parseInt(parts[3])]; //also this will be the last range filter that is returned...
        }
    });
    return zoom;
};

/**
 * Mithril component for the timeseries object
 */
charts.timeSeries = {
    view: function(ctrl, params){
        var vm = params.vm;
        var widget = params.widget;
        var parsedData = widget.display.parser(vm.requests[widget.display.reqRequests[0]].data, widget.levelNames, vm, widget);
        parsedData.zoom = charts.getZoomFromTimeRangeFilter(vm.requests[widget.display.reqRequests[0]]);
        var chartSetup = charts.timeSeriesChart(parsedData, vm, widget);
        return charts.updateC3(vm, chartSetup, widget.id);
    }
};

/**
 * Mithril component for the chart object
 */
charts.donut = {
    view: function(ctrl, params){
        var vm = params.vm;
        var widget = params.widget;
        var parsedData = widget.display.parser(vm.requests[widget.display.reqRequests[0]].data, widget.levelNames, vm, widget);
        var chartSetup = charts.donutChart(parsedData, vm, widget);
        return charts.updateC3(vm, chartSetup, widget.id);
    }
};

/**
 * Wraps and returns a c3 chart in a component, or updates already created chart
 * Only updates when an update to this widget has been requested
 *
 * @param {Object} c3ChartSetup: A fully setup c3 chart object
 * @param {Object} vm: vm of the searchDashboard
 * @param {Object} divID: id of the chart (name of widget)
 * @return {Object}  c3 chart wrapped in component
 */
charts.updateC3 = function(vm, c3ChartSetup, divID) {
    return m('div.c3-chart-padding', {id: divID,
                    config: function(element, isInit, context){
                        if (!isInit) {
                            vm.widgets[divID].handle = c3.generate(c3ChartSetup);
                            return vm.widgets[divID].handle;
                        }
                        if (!widgetUtils.updateTriggered(divID,vm)) {return; }
                        vm.widgets[divID].handle.load({
                            columns: c3ChartSetup.data.columns,
                            unload: true
                        });
                    }
            });
};

charts.getChangedColumns = function(oldCols, newCols){
    var changedCols = [];
    $.each(newCols, function(i, col){
        if($.inArray(col, oldCols) === -1) changedCols.push(col);
    });
};

/**
 * Creates a c3 donut chart component
 *
 * @param {Object} vm: vm of the searchDashboard
 * @param {Object} widget: params of the widget that chart is being created for
 * @return {Object} c3 chart wrapped in component
 */
charts.donutChart = function (data, vm, widget) {
    data.onclick = widget.display.callbacks.onclick ? widget.display.callbacks.onclick.bind({
        vm: vm,
        widget: widget
    }) : undefined;
    data.type = 'donut';

    return {
        bindto: '#' + widget.id,
        size: {
            height: widget.size[1]
        },
        data: data,
        donut: {
            title: widget.display.title ? widget.display.title : data.title,
            label: {format: widget.display.labelFormat || undefined}
        },
        legend: {
            show: true,
            position: 'right',
            item : {onclick: data.onclick}
        }
    };
};

/**
 * Creates a c3 histogram chart component //NOT USED, UNTESTED!
 *
 * @param {Object} vm: vm of the searchDashboard
 * @param {Object} widget: params of the widget that chart is being created for
 * @return {Object} c3 chart wrapped in component
 */
charts.barChart = function (data, vm, widget) {
    data.onclick = widget.display.callbacks.onclick ? widget.display.callbacks.onclick.bind({
        vm: vm,
        widget: widget
    }) : undefined;
    data.type = 'bar';

    return {
        bindto: '#' + widget.id,
        size: {
            height: widget.size[1],
        },
        data: data,
        tooltip: {
            grouped: false
        },
        legend: {
            position: 'right'
        },
        axis: {
            x: {
                tick: {
                    format: function (d) {return ''; },
                },
                label: {
                    text: widget.display.xLabel ? widget.display.xLabel : '',
                    position: 'outer-center'
                }
            },
            y: {
                label: {
                    text: widget.display.yLabel ? widget.display.yLabel : '',
                    position: 'outer-middle'
                },
                tick: {
                    format: function (x) {
                        if (x !== Math.floor(x)) {
                          return '';
                        }
                        return x;
                    }
                }
            },
            rotated: true
        }
    };
};

/**
 * Creates a c3 timeseries chart component after parsing raw data
 *
 * @param {Object} vm: vm of the searchDashboard
 * @param {Object} widget: params of the widget that chart is being created for
 * @return {Object}  c3 chart wrapped in component
 */
charts.timeSeriesChart = function (data, vm, widget) {
    data.type = widget.display.type ? widget.display.type : 'area-spline';
    if (!data.zoom && widget.handle) {widget.handle.unzoom(); }
    return {
        bindto: '#' + widget.id,
        size: {
            height: widget.size[1]
        },
        data: data,
        subchart: {
            show: true,
            size: {
                height: 30
            },
            onbrush: widget.display.callbacks.onbrushOfSubgraph ? widget.display.callbacks.onbrushOfSubgraph.bind({
                vm: vm,
                widget: widget,
                bounds: data.bounds,
            }) : undefined
        },
        axis: {
            x: {
                label: {
                    text: widget.display.xLabel ? widget.display.xLabel : '',
                    position: 'outer-center'
                },
                extent: data.zoom,
                type: 'timeseries',
                tick: {
                    format: function (d) {return widgetUtils.timeSinceEpochInMsToMMYY(d); }
                }
            },
            y: {
                label: {
                    text: widget.display.yLabel ? widget.display.yLabel : '',
                    position: 'outer-middle'
                },
                tick: {
                    format: function (x) {
                        if (x !== Math.floor(x)) {
                          return '';
                        }
                        return x;
                    }
                }
            }
        },
        legend: {
            position: 'inset',
            item: {
                onclick: widget.display.callbacks.onclickOfLegend ? widget.display.callbacks.onclickOfLegend.bind({
                    vm: vm,
                    widget: widget
                }) : undefined
            }
        },
        padding:{
            right: 15
        },
        tooltip: {
            grouped: false
        }
    };
};

/**
 * Parses a single level of elastic search data for a c3 single level chart (such as a donut)
 *
 * @param {Object} data: raw elastic aggregation Data to parse
 * @param {Object} levelNames: names of each level (one in this case)
 * @return {Object}  parsed data
 */
charts.singleLevelAggParser = function (data, levelNames, vm, widget) {
    var chartData = {};
    chartData.name = levelNames[0];
    chartData.columns = [];
    chartData.rawX = [];
    chartData.colors = {};
    chartData.type = 'donut';
    var count = 0;
    var hexColors = widget.display.customColors ?
        widget.display.customColors : charts.generateColors(data.aggregations[levelNames[0]].buckets.length);
    var i = 0;
    data.aggregations[levelNames[0]].buckets.forEach(
        function (bucket) {
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
 * @return {Object}  parsed data
 */
charts.twoLevelAggParser = function (data, levelNames, vm, widget) {
    var chartData = {};
    chartData.name = levelNames[0];
    chartData.columns = [];
    chartData.colors = {};
    chartData.x = 'x';
    chartData.groups = [];
    var grouping = [];
    grouping.push('x');
    var hexColors = widget.display.customColors ?
        widget.display.customColors : charts.generateColors(data.aggregations[levelNames[0]].buckets.length);
    var i = 0;
    var xCol = [];
    if(data.aggregations[levelNames[0]]) {
        data.aggregations[levelNames[0]].buckets.forEach(
            function (levelOneItem) {
                chartData.colors[levelOneItem.key] = hexColors[i];
                var column = [levelOneItem.key];
                grouping.push(levelOneItem.key);
                levelOneItem[levelNames[1]].buckets.forEach(function (levelTwoItem) {
                    column.push(levelTwoItem.doc_count);
                    if (i === 0) {
                        xCol.push(levelTwoItem.key);
                    }
                });
                chartData.columns.push(column);
                i = i + 1;
            }
        );
    }

    chartData.groups.push(grouping);
    xCol.unshift('x');
    chartData.columns.unshift(xCol);
    chartData.bounds = [chartData.columns[0][1], chartData.columns[0][chartData.columns[0].length-1]]; //get bounds of chart
    chartData.zoom = charts.getZoomFromTimeRangeFilter(vm.requests.mainRequest, chartData.bounds); //TODO the request name should not be here...
    return chartData;
};

module.exports = charts;
