'use strict';

var $ = require('jquery');
var m = require('mithril');
var moment = require('moment');
var $osf = require('js/osfHelpers');
var LogText = require('js/logTextParser');
var pips = require('sliderPips');

var xhrconfig = function (xhr) {
    xhr.withCredentials = true;
    xhr.setRequestHeader('Content-Type', 'application/vnd.api+json');
    xhr.setRequestHeader('Accept', 'application/vnd.api+json; ext=bulk');

};

var LogWrap = {
    controller: function(args){
        var self = this;
        self.wrapper = args.wrapper;
        self.activityLogs = m.prop();
        self.eventFilter = false; //holds the currently selected action category filter to include in request
        self.dateEnd = moment.utc();
        self.dateBegin = moment.utc();
        self.today = moment.utc();
        self.sixMonthsAgo = moment.utc().subtract(6, 'months');
        self.page = 1; //page currently shown on log container, related to queried page by ` page : ((self.page/2) | 0) + 1 `
        self.cache = []; //to store already requested with the current parameters
        self.loading = false; //keeps track of whether the log container should show the loading icon
        self.div = 8.64e+7; //milliseconds in day, for conversion with the slider bar
        self.monthDiv = 2629746000;  //milliseconds in a month
        self.canvasHeight = 40;
        self.totalEvents = 0; //initialization of count of all logs returned (total)
        self.eventNumbers = {}; //initialization of dict for aggregate counts (number of 'file' events, etc)
        self.commentEvents = 0;
        self.fileEvents = 0;
        self.wikiEvents = 0;
        self.nodeEvents = 0;
        self.otherEvents = 0;
        self.errorLoading = false;
        self.select = function(selector) {
            return $('#'+self.wrapper).find(selector);
        };

        self.getLogs = function(init, reset, update) {
            if (!(init || reset || update)  && self.cache[self.page - 1]){
                self.activityLogs(self.cache[self.page - 1]);
                if (!self.cache[self.page] && self.page < self.lastPage){
                    self.page = self.page + 1;
                    self.getLogs(false, false, true);
                    self.page = self.page - 1;
                }
                return;
            }
            var query = {
                'embed': ['nodes', 'user', 'linked_node', 'template_node'],
                'page': ((self.page/2) | 0) + 1,
                'page[size]': 20
            };
            if (self.eventFilter) {
                query['filter[action]'] = self.eventFilter;
            }
            if (reset || init) {
                query.aggregates = 1;
            }
            if (!init) {
                query['filter[date][lte]'] = self.dateEnd.toISOString();
                query['filter[date][gte]'] = self.dateBegin.toISOString();
            }
            var url = $osf.apiV2Url('users/me/logs/', { query : query });
            var promise = m.request({method : 'GET', url : url, config : xhrconfig, background: (update ? true : false)});
            promise.then(function _requestSuccess(result){
                self.loading = false;
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                });
                if (init) {
                    self.lastDay = moment.utc(result.data[0].attributes.date);
                    self.dateEnd = self.lastDay;
                    var firstDay = moment.utc(result.meta.last_log_date);
                    self.firstDay = ((firstDay >= self.sixMonthsAgo) ? firstDay : self.sixMonthsAgo).startOf('month');
                    var dateBegin = moment.utc(result.data[0].attributes.date).subtract(1, 'months');
                    self.dateBegin = ((dateBegin > self.firstDay) ? dateBegin : self.firstDay).startOf('day');
                    if ((self.today - self.firstDay)/self.monthDiv < 1){ //check if the slider will be less than a month
                        self.div = self.div/4; //then set division to be for a 1/4 day instead of a day
                        self.formatFloat = 'Do h a';
                        self.steps = 14;
                        self.formatPip = 'MMM Do';
                    } else if ((self.today - self.firstDay)/self.monthDiv < 3){
                        self.div = self.div/2;
                        self.formatFloat = 'MMM Do h';
                        self.steps = 28;
                        self.formatPip = 'MMM Do';
                    } else {
                        self.formatFloat = 'MMM Do';
                        self.steps = 31;
                        self.formatPip = 'MMM';
                    }
                }
                if (reset){
                    self.totalEvents = result.links.meta.total;
                    self.eventNumbers = result.meta.aggregates;
                    self.fileEvents = ((self.eventNumbers.files/self.totalEvents)*100 | 0) + (self.eventNumbers.files ? 5 : 0);
                    self.commentEvents = ((self.eventNumbers.comments/self.totalEvents)*100 | 0) + (self.eventNumbers.comments ? 5 : 0);
                    self.wikiEvents = ((self.eventNumbers.wiki/self.totalEvents)*100 | 0) + (self.eventNumbers.wiki ? 5 : 0);
                    self.nodeEvents = ((self.eventNumbers.nodes/self.totalEvents)*100 | 0) + (self.eventNumbers.nodes ? 5 : 0);
                    self.otherEvents = 100 - (self.fileEvents + self.commentEvents + self.wikiEvents + self.nodeEvents);
                    self.cache = [];
                }
                if (!init) {
                    self.cache.push(result.data.slice(0,9));
                    self.cache.push(result.data.slice(10,19));
                    if (!update) {
                        self.activityLogs(self.cache[self.page - 1]);
                    }
                }
                self.lastPage = (result.links.meta.total / (result.links.meta.per_page/2) | 0) + 1;
            }, function _requestFail(){
                self.errorLoading = true;
                self.activityLogs([]);
            });
            return promise;
        };

        self.callLogs = function(filter) {
            self.eventFilter = self.eventFilter === filter ? false : filter;
            self.page = 1;
            self.cache = [];
            self.getLogs();
        };

        self.getLogs(true, false);

        $(window).resize(function(){
            var canvas = document.getElementById('rACanvas');
            var ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        });

        self.makeLine = function(canvas){
            var ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            var progBar = self.select('#rAProgressBar');
            var canvasElement = self.select('#rACanvas');
            var handle = $('.ui-slider-handle');
            var leftHandle = handle[0];
            var rightHandle = handle[1];
            ctx.beginPath();
            ctx.moveTo(leftHandle.offsetLeft + (handle.width()/2), 0);
            ctx.lineTo(progBar.offset().left - canvasElement.offset().left, self.canvasHeight);
            ctx.strokeStyle = '#E0E0E0 ';
            ctx.lineWidth = 2;
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(rightHandle.offsetLeft + (handle.width()/2), 0);
            ctx.lineTo(progBar.offset().left + progBar[0].offsetWidth - canvasElement.offset().left, self.canvasHeight);
            ctx.strokeStyle = '#E0E0E0 ';
            ctx.lineWidth = 2;
            ctx.stroke();
        };
        self.categoryColor = function(category){
            if (category.indexOf('wiki') !== -1){ return '#d9534f'; }
            if (category.indexOf('comment') !== -1){ return '#5bc0de'; }
            if (category.indexOf('file') !== -1){ return '#337ab7'; }
            if (category.indexOf('project') !== -1){ return '#f0ad4e'; }
            else { return '#5cb85c'; }
        };
        self.addButtons = function(ele, isInitialized) {
            if (self.select('#rALeftButton')){
                self.select('#rALeftButton').css('height', self.select('#rALogs').height());
            }
            if (self.select('#rARightButton')){
                self.select('#rARightButton').css('height', self.select('#rALogs').height());
            }
        };
        self.sliderProgress = '<div id="rAFilleBar" class="progress" style="height: 11px"><div class="progress-bar"></div></div>';
        self.addSlider = function(ele, isInitialized){
            var begin = (Number(self.firstDay.format('x'))/self.div | 0);
            var end = (Number(self.today.format('x'))/self.div | 0);
            var values = [(Number(self.dateBegin.format('x'))/self.div | 0), (Number(self.dateEnd.format('x'))/self.div | 0)];
            var canvas = document.getElementById('rACanvas');
            var sliderElement = self.select('#rASlider');
            if (!isInitialized) {
                sliderElement.slider({
                    min: begin,
                    max: end,
                    range: true,
                    values: values,
                    stop: function (event, ui) {
                        self.page = 1;
                        self.dateBegin = moment.utc(ui.values[0]*self.div);
                        self.dateEnd = moment.utc(ui.values[1]*self.div);
                        self.eventFilter = false;
                        self.getLogs(false, true);
                    },
                    start: function (event, ui){
                        self.eventFilter = false;
                        self.loading = true;
                        m.redraw();
                        self.select('#rAFilleBar').replaceWith(
                            '<div id="rAFilleBar" class="progress" style="height: 11px">' +
                                '<div class="progress-bar progress-bar-success progress-bar-striped active" style="width:100%;"></div>' +
                            '</div>'
                        );
                    },
                    slide: function (){
                        self.makeLine(canvas);
                    },
                    change: function (event, ui){
                        self.loading = true;
                        m.redraw();
                        self.select('#rAFilleBar').replaceWith(
                            '<div id="rAFilleBar" class="progress" style="height: 11px">' +
                                '<div class="progress-bar progress-bar-success progress-bar-striped active" style="width:100%;"></div>' +
                            '</div>'
                        );
                        self.page = 1;
                        self.dateBegin = moment.utc(ui.values[0]*self.div);
                        self.dateEnd = moment.utc(ui.values[1]*self.div);
                        self.eventFilter = false;
                        self.getLogs(false, true);
                    }
                });
                sliderElement.slider('pips', {
                    last: false,
                    rest: 'label',
                    step: self.steps,
                    formatLabel: function(value){
                        return String(moment.utc(value*self.div).format(self.formatPip));
                    }
                }).slider('float', {
                    formatLabel: function(value){
                        return String(moment.utc(value*self.div).format(self.formatFloat));
                    }
                });
                self.getLogs(false, true);
                var bar = sliderElement.find('.ui-slider-range');
                bar.append(self.sliderProgress);
                self.makeLine(canvas);
            }
            else {
                self.select('#rAFilleBar').replaceWith(self.sliderProgress);
                self.makeLine(canvas);
            }
        };
    },

    view: function(ctrl, args){
        if (ctrl.errorLoading){
            return m('p', {style: {textAlign: 'center'}}, 'Error loading logs. Please refresh the page.');
        }

        var fileEvents = ctrl.fileEvents;
        var commentEvents = ctrl.commentEvents;
        var wikiEvents = ctrl.wikiEvents;
        var nodeEvents = ctrl.nodeEvents;
        var otherEvents = ctrl.otherEvents;
        var filterLabels = function(){
            if (!ctrl.eventFilter){
                if (otherEvents === 100) {
                    return m('p', 'No filters available');
                }
                return m('p', [
                    'Filter on: ',
                    fileEvents ? m('a', {onclick: function(){ctrl.callLogs('file')}}, 'Files' + (nodeEvents || commentEvents || wikiEvents ? ', ': '')): '', // jshint ignore:line
                    nodeEvents ? m('a', {onclick: function(){ctrl.callLogs('project')}}, 'Projects' + (commentEvents || wikiEvents ? ', ': '')): '', // jshint ignore:line
                    commentEvents ? m('a', {onclick: function(){ctrl.callLogs('comment')}}, 'Comments' + (wikiEvents ? ', ': '')): '',// jshint ignore:line
                    wikiEvents ? m('a', {onclick: function(){ctrl.callLogs('wiki')}}, 'Wiki'): '' // jshint ignore:line
                ]);
            } else {
                return m('p', [
                    m('span','Filtering on '),
                    m('b', (ctrl.eventFilter === 'file' ? 'Files' : ctrl.eventFilter === 'project' ? 'Projects' : ctrl.eventFilter === 'comment' ? 'Comments' : 'Wiki') + ' '),
                    m('span.badge.pointer.m-l-xs', {
                        onclick: function(){ ctrl.callLogs(ctrl.eventFilter); },
                    }, [ m('i.fa.fa-close'), ' Clear'])
                ]);
            }
        };
        return m('.fb-activity-list.col-md-10.col-md-offset-1.m-t-xl#' + ctrl.wrapper, [
                m('.time-slider-parent',
                    m('#rASlider',  {config: ctrl.addSlider})
                ),
                m('canvas#rACanvas', {
                    style: {verticalAlign: 'middle'},
                    width: $('#rASlider').width(),
                    height: ctrl.canvasHeight
                }),
                m('.row', [
                    m('.col-xs-10.col-xs-offset-1',
                        m('#rAProgressBar.progress.category-bar',
                            ctrl.loading ? m('.progress-bar.progress-bar-success.active.progress-bar-striped', {style: {width: '100%'}}, m('b', {style:{color: 'white'}}, 'Loading')) : ([
                                m('a.progress-bar' + (ctrl.eventFilter === 'file' ||  ctrl.eventFilter === false ?  '.selected' : ''), {style: {width: fileEvents+'%'},
                                    onclick: function(){
                                        ctrl.callLogs('file');
                                    }}, m('i.fa.fa-file.progress-bar-button')
                                ),
                                m('a.progress-bar.progress-bar-warning' + (ctrl.eventFilter === 'project' ||  ctrl.eventFilter === false ?  '.selected' : ''), {style: {width: nodeEvents+'%'},
                                    onclick: function(){
                                        ctrl.callLogs('project');
                                    }},  m('i.fa.fa-cube.progress-bar-button')
                                ),
                                m('a.progress-bar.progress-bar-info' + (ctrl.eventFilter === 'comment' || ctrl.eventFilter === false ?  '.selected' : ''), {style: {width: commentEvents+'%'},
                                    onclick: function(){
                                        ctrl.callLogs('comment');
                                    }}, m('i.fa.fa-comment.progress-bar-button')
                                ),
                                m('a.progress-bar.progress-bar-danger' + (ctrl.eventFilter === 'wiki' || ctrl.eventFilter === false ?  '.selected' : ''), {style: {width: wikiEvents+'%'},
                                    onclick: function(){
                                        ctrl.callLogs('wiki');
                                    }}, m('i.fa.fa-book.progress-bar-button')
                                ),
                                (ctrl.totalEvents !== 0) ?
                                    m('.progress-bar.progress-bar-success', {style: {width: otherEvents+'%'}}, m('i.fa.fa-plus.progress-bar-button')) :
                                    m('.progress-bar.no-items-progress-bar', 'None')
                            ])
                        )
                    )
                ]),
                m('.row', !ctrl.loading ? [m('.col-xs-10.col-xs-offset-1', filterLabels())] : ''),
                 !ctrl.loading ?
                m('.row',{style:{paddingTop: '15px'}}, [
                    m('.col-xs-1', m('#rALeftButton' + (ctrl.page > 1 ? '' : '.disabled.hidden'), {
                        onclick: function(){
                            ctrl.page--;
                            ctrl.getLogs();
                        }},m('i.fa.fa-angle-left.page-button'))),
                    m('#rALogs.col-xs-10' ,(ctrl.activityLogs() && (ctrl.activityLogs().length > 0))? ctrl.activityLogs().map(function(item){
                        return m('.activity-item',
                            {style: {borderLeft: 'solid 5px ' + ctrl.categoryColor(item.attributes.action)}}, [
                            m('span.text-muted.m-r-xs', item.attributes.formattableDate.local),
                            m.component(LogText,item)
                        ]);
                    }) : m('p','No activity in this time range.')),
                    m('.col-xs-1', {config: ctrl.addButtons}, m('#rARightButton' + (ctrl.lastPage > ctrl.page ? '' : '.disabled.hidden'),{
                        onclick: function(){
                            ctrl.page++;
                            ctrl.getLogs();
                        }
                    }, m('i.fa.fa-angle-right.page-button' )))
                ]) : m('.spinner-loading-wrapper', [m('.logo-spin.logo-md'), m('p.m-t-sm.fg-load-message', 'Loading logs...')]),
                !ctrl.loading ? m('p.activity-pages.m-t-md.text-center', ctrl.page + ' of ' + ctrl.lastPage) : '',
            ]);
    }
};

module.exports = LogWrap;
