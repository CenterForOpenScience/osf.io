'use strict';

var c3 = require('c3');
require('c3/c3.css');
var d3 = require('c3/node_modules/d3');

var pikaday = require('pikaday');
require('pikaday-css');

var moment = require('moment');

var sparkline = require('jquery-sparkline');

var ko = require('knockout');
var $osf = require('js/osfHelpers');

var ctx = window.contextVars;

var guidStatsItem = function(guid, title, data, dataType) {
    var self = this;
    self.guid = guid;
    self.title = title;
    self.data = data;
    self.total = ko.computed(function(){
        if(dataType == 'Unique Visitors' || dataType == 'Unique Page Views'){
            return d3.max(data);
        }
        return d3.sum(data);
    });

};

var StatisticsViewModel = function() {

    var self = this;

    var childrenRenderLimit = 0;
    var filesRenderLimit = 0;

    self.dates = [];
    self.dataType = ko.observable('Visits');
    self.piwikDataType = ko.computed(function(){
        switch (self.dataType()){
            case 'Visits':
                return 'nb_visits';

            case 'Unique Visitors':
                return 'nb_uniq_visitors';

            case 'Page Views':
                return 'nb_pageviews';

            case 'Unique Page Views':
                return 'nb_uniq_pageviews';
        }
    });

    self.method = ko.computed(function() {
        if (self.dataType() == 'Page Views' || self.dataType() == 'Unique Page Views'){
            return 'Actions.get'
        }
        return 'VisitsSummary.get'
    });

    self.period = ko.observable('day');
    self.date = ko.observable(function() {
        return moment().subtract(30, 'days').format('YYYY-MM-DD') + ',' + moment().format('YYYY-MM-DD');
    }());

    self.node = ko.observableArray([]);
    self.children = ko.observableArray([]);
    self.files = ko.observableArray([]);
    self.dataTypeOptions = ko.observableArray(['Visits', 'Page Views', 'Unique Visitors', 'Unique Page Views']);
    self.optionsButtonHTML = ko.computed(function(){
        return self.dataType() + ' ' + '<span class="fa fa-caret-down"></span>';
    });

    self.dateButtonHTML = ko.computed(function(){
        var dates = self.date().split(',');
        if($('#dateRange').prop('checked')){
            return 'Date Range: ' + dates[0] + ' to ' + dates[1] + ' <span class="fa fa-calendar"></span>';
        }
        return 'Date Range: ' + dates[1] + ' <span class="fa fa-calendar"></span>';
    });

    self.renderChildren = ko.observableArray();
    self.renderFiles = ko.observableArray();


    self.currentPiwikParams = ko.computed(function() {
        return {
            dataType: self.dataType(),
            method: self.method(),
            period: self.period(),
            date: self.date(),
            files: JSON.stringify(nodeFiles)
        }
    });

    var startPicker = new pikaday({
        field: document.getElementById('startPickerField'),
        format: 'YYYY-MM-DD',
        maxDate: moment().toDate(),
        onSelect: function(){
            if($('#date').prop('checked')) {
                var end = startPicker.getMoment();
                var start = moment(end).subtract(30, 'days');

                self.date(start.format('YYYY-MM-DD') + ',' + end.format('YYYY-MM-DD'));
            }
            startPicker.setStartRange(startPicker.getMoment().toDate());
            endPicker.setStartRange(startPicker.getMoment().toDate());
            endPicker.setMinDate(startPicker.getMoment().toDate());

            if($('#dateRange').prop('checked') && endPicker.toString() != ''){
                self.date(startPicker.toString() + ',' + endPicker.toString());
            }
        }
    });

    var endPicker = new pikaday({
        field: document.getElementById('endPickerField'),
        format: 'YYYY-MM-DD',
        maxDate: moment().toDate(),
        onSelect: function(){
            startPicker.setEndRange(endPicker.getMoment().toDate());
            endPicker.setEndRange(endPicker.getMoment().toDate());

            self.date(startPicker.toString() + ',' + endPicker.toString());

        }

    });

    self.formatStatistics = function(nodeData, fileData){
        self.dates = nodeData['dates'];
        self.node(self.guidStatsItemize(nodeData['node']));
        self.children(self.guidStatsItemize(nodeData['children']));
        self.files(self.guidStatsItemize(fileData['files']));

        self.renderMore('children');
        self.renderMore('files');

    };

    self.guidStatsItemize = function(data) {
        return data.map(function(item) {
            return new guidStatsItem(item.node_id, item.title, self.piwikDataToArray(item.data), self.dataType());
        }).sort(function(a, b){
            return b.total() - a.total();
        });

    };

    self.piwikDataToArray = function(piwikData) {
        var data = [];

        for(var i=0; i<self.dates.length; i++){
            var date = self.dates[i];
            if($.isPlainObject(piwikData[date])){
                data.push(piwikData[date][self.piwikDataType()]);
            } else {
                data.push(0);
            }
        }
        return data;
    };

    self.getData = function() {

        return $.when(
            $.get('http://localhost:7000/'+ ctx.node.id +'/nodeData', self.currentPiwikParams()),
            $.get('http://localhost:7000/fileData', self.currentPiwikParams())
        ).then(function(nodeData, fileData) {
                self.formatStatistics(nodeData[0], fileData[0]);
            },
            function(){
                console.log(arguments)
            });
    };

    self.chart = function() {
        var dates = self.dates.slice(0);
        var data = self.node().slice(0)[0].data;

        var chartMax = d3.max(data) < 10 ? 10 : null;

        dates.unshift('x');
        data.unshift(self.dataType());

        c3.generate({
            bindto: '.piwikChart',
            size: {
                height: 400
            },
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
                        format: '%Y-%m-%d',
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
                    },
                    max: chartMax
                }
            },
            padding: {
                right: 50,
                bottom: 20
            }
        });
    };

    ko.bindingHandlers.sparkline = {
        update: function(element, valueAccessor) {
            var value = valueAccessor();
            var guidStatsItem = ko.unwrap(value);

            var sparkId = '#' + $(element).prop('id');

            $(sparkId).sparkline( guidStatsItem.data,
            {
                lineColor: '#204762',
                fillColor: '#EEEEEE',
                spotColor: '#337ab7',
                width: '100%',
            });
        }
    };

    self.redrawSparkLines = function() {
        for (var i = 0; i < self.renderChildren().length; i++) {
            var guidStatsItem = self.renderChildren()[i];
            var sparkId = '#' + guidStatsItem.guid + 'Spark';
            $(sparkId).empty();
        }

        for (var i = 0; i < self.renderFiles().length; i++) {
            var guidStatsItem = self.renderFiles()[i];
            var sparkId = '#' + guidStatsItem.guid + 'Spark';
            $(sparkId).empty();
        }

        for (var i = 0; i < self.renderChildren().length; i++) {
            var guidStatsItem = self.renderChildren()[i];
            var sparkId = '#' + guidStatsItem.guid + 'Spark';
            $(sparkId).sparkline( guidStatsItem.data,
            {
                lineColor: '#204762',
                fillColor: '#EEEEEE',
                spotColor: '#337ab7',
                width: '100%'
            });
        }

        for (var i = 0; i < self.renderFiles().length; i++) {
            var guidStatsItem = self.renderFiles()[i];
            var sparkId = '#' + guidStatsItem.guid + 'Spark';
            $(sparkId).sparkline( guidStatsItem.data,
            {
                lineColor: '#204762',
                fillColor: '#EEEEEE',
                spotColor: '#337ab7',
                width: '100%'
            });
        }

    };

    self.renderMore = function(type) {
        if(type == 'children'){
            childrenRenderLimit += 1;
            if(childrenRenderLimit > self.children().length){
                self.renderChildren(self.children().slice(0));
            } else {
                self.renderChildren(self.children().slice(0, childrenRenderLimit));
            }
        }

        if(type == 'files') {
            filesRenderLimit += 1;
            if(filesRenderLimit > self.files().length){
                self.renderFiles(self.files().slice(0));
            } else {
                self.renderFiles(self.files().slice(0, filesRenderLimit));
            }
        };

    };

    self.changeDataType = function(dataTypeOption) {
        self.dataType(dataTypeOption);
    };

    self.updateStats = function() {
        self.getData().then(function() {
            self.chart();
        })
    };

    self.currentPiwikParams.subscribe(function() {
        self.updateStats();
    });

    //Load initial statistics: Visits
    self.init = function() {
        $('#date').on('change', function() {
            $('#endPickerField').toggleClass('hidden');
            startPicker.setStartRange(null);
            startPicker.setEndRange(null);
            endPicker.setStartRange(null);
            endPicker.setEndRange(null);
        });
        $('#dateRange').on('change', function() {
            $('#endPickerField').toggleClass('hidden');
        });
        return self.getData();
    };

};

function Statistics(selector) {
    var self = this;
    self.viewModel = new StatisticsViewModel();
    self.viewModel.init().then(function() {
        $osf.applyBindings(self.viewModel, selector);
        self.viewModel.chart();
        $(window).resize($osf.debounce(function(){
                self.viewModel.redrawSparkLines();
            }, 100, true));

    });

}

module.exports = Statistics;
