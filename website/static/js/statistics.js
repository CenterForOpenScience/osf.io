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

var guidStatsItem = function(guid, title, data) {
    var self = this;
    self.guid = guid;
    self.title = title;
    self.data = data;
    self.total = ko.computed(function(){
        var total = 0;
        for(var i=0; i<self.data.length; i++){
            total  += self.data[i];
        }

        return total;
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
            case "Visits":
                return "nb_visits";

            case "Unique Visitors":
                return "nb_uniq_visitors";

            case "Page Views":
                return "nb_pageviews";

            case "Unique Page Views":
                return "nb_uniq_pageviews";
        }
    });

    self.method = ko.computed(function() {
        if (self.dataType() == "Page Views" || self.dataType() == "Unique Page Views"){
            return "Actions.get"
        }
        return "VisitsSummary.get"
    });

    self.period = ko.observable('day');

    self.pikadayDate = ko.observable(moment().format('YYYY-MM-DD'));

    self.date = ko.computed(function() {
        var endDate = moment(self.pikadayDate());
        var startDate = moment(endDate).subtract(30, 'days');

        return startDate.format('YYYY-MM-DD') + ',' + endDate.format('YYYY-MM-DD');
    });

    self.node = ko.observableArray([]);
    self.children = ko.observableArray([]);
    self.files = ko.observableArray([]);
    self.dataTypeOptions = ko.observableArray(['Visits', 'Page Views', 'Unique Visitors', 'Unique Page Views']);
    self.optionsButtonHTML = ko.computed(function(){
        return self.dataType() + ' ' + '<span class="fa fa-caret-down"></span>';
    });

    self.dateButtonHTML = ko.computed(function(){
        var dates = self.date().split(',');
        return dates[1] + ' <span class="fa fa-calendar"></span>';
    });

    self.renderChildren = ko.observableArray();
    self.renderFiles = ko.observableArray();


    self.currentPiwikParams = ko.computed(function() {
        return {
            dataType: self.dataType(),
            method: self.method(),
            period: self.period(),
            date: self.date(),
            files: nodeFiles
        }
    });

    var picker = new pikaday({
        field: document.getElementById('datePickerField'),
        trigger: document.getElementById('datePickerButton'),
        onSelect: function(){
            self.pikadayDate(picker.toString());
        }
    });

    var endPicker = new pikaday({
        field: document.getElementById('endDatePickerField'),
        trigger: document.getElementById('datePickerButton'),
        onSelect: function(){
            self.pikadayDate(endPicker.toString());
        }
    });

    self.formatStatistics = function(nodeData, fileData){
        self.dates = nodeData['dates'];
        self.node(self.guidStatsItemize(nodeData['node']));
        self.children(self.guidStatsItemize(nodeData['children']));
        self.files(self.guidStatsItemize(fileData['files']));

        self.renderMore('children');
        self.renderMore();

    };

    self.guidStatsItemize = function(data) {
        return data.map(function(item) {
            return new guidStatsItem(item.node_id, item.title, self.piwikDataToArray(item.data));
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

    self.renderSparkLines = function() {
        for (var i = 0; i < self.renderChildren().length; i++) {
            var guidItem = self.renderChildren()[i];
            var sparkId = '#' + guidItem.guid + 'Spark';
            $(sparkId).empty();
        }

        for (var i = 0; i < self.renderFiles().length; i++) {
            var guidItem = self.renderFiles()[i];
            var sparkId = '#' + guidItem.guid + 'Spark';
            $(sparkId).empty();
        }

        for (var i = 0; i < self.renderChildren().length; i++) {
            var guidItem = self.renderChildren()[i];
            var sparkId = '#' + guidItem.guid + 'Spark';
            $(sparkId).sparkline( guidItem.data,
            {
                lineColor: '#204762',
                fillColor: '#EEEEEE',
                spotColor: '#337ab7',
                width: '100%'
            });
        }

        for (var i = 0; i < self.renderFiles().length; i++) {
            var guidItem = self.renderFiles()[i];
            var sparkId = '#' + guidItem.guid + 'Spark';
            $(sparkId).sparkline( guidItem.data,
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
            childrenRenderLimit += 5;
            if(childrenRenderLimit > self.children().length){
                self.renderChildren(self.children().slice(0));
            } else {
                self.renderChildren(self.children().slice(0, childrenRenderLimit));
            }
        } else {
            filesRenderLimit += 5;
            if(filesRenderLimit > self.files().length){
                self.renderFiles(self.files().slice(0));
            } else {
                self.renderFiles(self.files().slice(0, filesRenderLimit));
            }
        }
    };

    self.changeDataType = function(dataTypeOption) {
        self.dataType(dataTypeOption);
    };

    self.updateStats = function() {
        self.getData().then(function() {
            self.chart();
            self.renderSparkLines();
        })
    };

    self.currentPiwikParams.subscribe(function() {
        self.updateStats();
    });

    //Load initial statistics: Visits
    self.init = function() {
        return self.getData();
    };

};

function Statistics(selector) {
    var self = this;
    self.viewModel = new StatisticsViewModel();
    self.viewModel.init().then(function() {
        $osf.applyBindings(self.viewModel, selector);
        self.viewModel.chart();
        self.viewModel.renderSparkLines();
        $(window).resize($osf.debounce(function(){
                self.viewModel.renderSparkLines();
            }, 100, true));

    });

}

module.exports = Statistics;
