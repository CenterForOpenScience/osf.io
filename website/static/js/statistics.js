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

    self.childrenRenderLimit = ko.observable(5);
    self.filesRenderLimit = ko.observable(5);

    self.nodeTitle = ctx.node.title;

    self.dates = [];
    self.dataType = ko.observable('Visits');
    self.piwikDataType = function(){
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
    };

    self.method = function() {
        if (self.dataType() == 'Page Views' || self.dataType() == 'Unique Page Views'){
            return 'Actions.get'
        }
        return 'VisitsSummary.get'
    };

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
            return 'Date: ' + dates[0] + ' to ' + dates[1] + ' <span class="fa fa-calendar"></span>';
        }
        return 'Date: ' + dates[1] + ' <span class="fa fa-calendar"></span>';
    });

    self.renderChildren = ko.computed(function(){
        if(self.childrenRenderLimit() > self.children().length){
            return self.children().slice(0);
        } else {
            return self.children().slice(0, self.childrenRenderLimit());
        }

    });
    self.renderFiles = ko.computed(function(){
        if(self.filesRenderLimit() > self.files().length){
            return self.files().slice(0);
        } else {
            return self.files().slice(0, self.filesRenderLimit());
        }
    });


    self.currentPiwikParams = ko.computed(function() {
        return {
            nodeId: ctx.node.id,
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
            $.get('http://localhost:7000/statistics', self.currentPiwikParams())
        ).then(function(projectData) {
                self.formatStatistics(projectData['node_data'], projectData['files_data']);
            },
            function(){
                /* Catch all until Tornadik specific error handlers implemented */
                $osf.growl('Error', 'An error has occurred in retrieving project statistics.');
                self.dates = [];
                self.node([]);
                self.children([]);
                self.files([]);
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
                width: '100%'
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

    self.incrementChildrenLimit = function() {
        self.childrenRenderLimit(self.childrenRenderLimit() + 1);
    };

    self.incrementFilesLimit = function() {
        self.filesRenderLimit(self.filesRenderLimit() + 5);
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

    /* Load initial statistics: Visits */
    self.init = function() {
        $('#date').on('change', function() {
            $('#endPickerField').toggleClass('hidden');
            startPicker.setStartRange(null);
            startPicker.setEndRange(null);
            endPicker.setStartRange(null);
            endPicker.setEndRange(null);
            $('#startPickerField').attr('placeholder', 'Select a date');
        });
        $('#dateRange').on('change', function() {
            $('#endPickerField').toggleClass('hidden');
            $('#startPickerField').attr('placeholder', 'Select start date');
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

    }, function() {
        $osf.applyBindings(self.viewModel, selector);
        $('.panel-body').each(function(){
            $(this).html('<h4 class="text-center text-danger">Error retrieving data</h4>')
        })
    });

}

module.exports = Statistics;
