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
    this.guid = guid;
    this.title = title;
    this.data = data;
    this.total = ko.computed(function(){
        var total = 0;
        for(var i=0; i<this.data.length; i++){
            total  += this.data[i];
        }

        return total;
    }, this);

};

var StatisticsViewModel = function() {

    var self = this;

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
    self.date = ko.computed(function(date){

    });

    self.node = ko.observableArray([]);
    self.children = ko.observableArray([]);
    self.files = ko.observableArray([]);
    self.dataTypeOptions = ko.observableArray(['Visits', 'Page Views', 'Unique Visitors', 'Unique Page Views']);
    self.optionsButtonHTML = ko.computed(function(){
        return self.dataType() + ' ' + '<span class="fa fa-caret-down"></span>';
    });


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
        trigger: document.getElementById('datepickerButton'),
        onSelect: function(){
            self.date(picker.toString());
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
            return new guidStatsItem(item.node_id, item.title, self.piwikDataToArray(item.data));
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

    self.changeDataType = function(dataTypeOption) {
        self.dataType(dataTypeOption);
    };

    self.updateStats = function() {
        self.getData().then(function() {
            self.chart();
        })
    };

    self.dataType.subscribe(function() {
        self.updateStats();
    });

    //Load initial statistics: Visits
    self.init = function() {
        return self.getData();
    }

};

function Statistics(selector) {
    var self = this;
    self.viewModel = new StatisticsViewModel();
    self.viewModel.init().then(function() {
        $osf.applyBindings(self.viewModel, selector);
        self.viewModel.chart();
    });

}

module.exports = Statistics;
