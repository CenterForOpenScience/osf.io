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
        self.userId = args.userId;
        self.activityLogs = m.prop();
        self.eventFilter = false;
        self.dateEnd = moment.utc();
        self.dateBegin = moment.utc();
        self.today = moment.utc();
        self.page = 1;
        self.cache = [];

        self.getLogs = function(init, reset) {
            if (!(init || reset)  && self.cache[self.page - 1]){
                self.activityLogs(self.cache[self.page - 1]);
                return
            }
            var query = {
                'embed': ['nodes', 'user', 'linked_node', 'template_node'],
                'page': ((self.page/2) | 0) + 1,
                'page[size]': 20
            };
            if (self.eventFilter) {
                query['filter[action]'] = self.eventFilter;
            }
            if (init || reset) {
                query['aggregate'] = 1;
            }
            if (!init) {
                query['filter[date][lte]'] = self.dateEnd.toISOString();
                query['filter[date][gte]'] = self.dateBegin.toISOString();
            }
            var url = $osf.apiV2Url('users/' + self.userId + '/node_logs/', { query : query});
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                });
                if (init) {
                    self.lastDay = moment.utc(result.data[0].attributes.date);
                    self.dateEnd = self.lastDay;
                    self.dateBegin = moment.utc(result.data[0].attributes.date).subtract(1, 'months');
                    self.firstDay = moment.utc(result.links.meta.last_log_date);
                }
                if (init || reset){
                    self.totalEvents = result.links.meta.total;
                    self.eventNumbers = result.links.meta.aggregates;
                    self.cache = [];
                }
                if (!init) {
                    self.cache.push(result.data.slice(0,9));
                    self.cache.push(result.data.slice(10,19));
                    self.activityLogs(self.cache[self.page - 1]);
                }
                self.lastPage = (result.links.meta.total / result.links.meta.per_page | 0) + 1;
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
    },
    view: function(ctrl, args){
        var fileEvents = ((ctrl.eventNumbers.files/ctrl.totalEvents)*100 | 0);
        var commentEvents = ((ctrl.eventNumbers.comments/ctrl.totalEvents)*100 | 0);
        var wikiEvents = ((ctrl.eventNumbers.wiki/ctrl.totalEvents)*100 | 0);
        var nodeEvents = ((ctrl.eventNumbers.nodes/ctrl.totalEvents)*100 | 0);
        var otherEvents = 100 - (fileEvents + commentEvents + wikiEvents + nodeEvents);
        var div = 8.64e+7;
        var begin = (Number(ctrl.firstDay.format('x'))/div | 0);
        var end = (Number(ctrl.today.format('x'))/div | 0);
        var values = [(Number(ctrl.dateBegin.format('x'))/div | 0), (Number(ctrl.dateEnd.format('x'))/div | 0)];
        var addSlider = function(ele, isInitialized){
            if (!isInitialized) {
                $("#recentActivitySlider").slider({
                    min: begin,
                    max: end,
                    range: true,
                    values: values,
                    stop: function (event, ui) {
                        ctrl.page = 1;
                        ctrl.dateBegin = moment.utc(ui.values[0]*div);
                        ctrl.dateEnd = moment.utc(ui.values[1]*div);
                        ctrl.getLogs(false, true);
                    }
                });
                $("#recentActivitySlider").slider('pips', {
                    last: false,
                    rest: 'label',
                    step: 30,
                    formatLabel: function(value){
                        return String(moment.utc(value*div).format("MMM D YY"))
                    }
                }).slider('float', {
                    formatLabel: function(value){
                        return String(moment.utc(value*div).format("MMM D YY"))
                    }
                });
                ctrl.getLogs();
            }
            else {
                $("#recentActivitySlider").slider('option', "values", values);
            }
        };
        var categoryColor = function(category){
            if (category.indexOf('wiki') + 1){
                return '#d9534f'
            }
            if (category.indexOf('comment') + 1){
                return '#5bc0de'
            }
            if (category.indexOf('file') + 1){
                return '#337ab7'
            }
            if (category.indexOf('project') + 1){
                return '#f0ad4e'
            }
            else{
                return '#5cb85c'
            }
        };
        return m('.panel.panel-default', [
            m('.panel-heading', 'Recent Activity'),
            m('.panel-body',
            m('.fb-activity-list.m-t-md', [
                m('', {style: {paddingBottom: '25px'}},
                    m('#recentActivitySlider', {style: {margin: '10px'}, config: addSlider})
                ),
                m('.progress', {style: {borderRadius: '25px'}}, [
                    m('.progress-bar' + (ctrl.eventFilter === 'file' ? '.active.progress-bar-striped' : '.muted'), {style: {width: fileEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.callLogs('file');
                        }, style: {color: 'white'}}, m('i.fa.fa-file'))
                    ),
                    m('.progress-bar.progress-bar-warning' + (ctrl.eventFilter === 'project' ? '.active.progress-bar-striped' : '.muted'), {style: {width: nodeEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.callLogs('project');
                        }, style: {color: 'white'}}, m('i.fa.fa-cube'))
                    ),
                    m('.progress-bar.progress-bar-info' + (ctrl.eventFilter === 'comment' ? '.active.progress-bar-striped' : '.muted'), {style: {width: commentEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.callLogs('comment');
                        }, style: {color: 'white'}}, m('i.fa.fa-comment'))
                    ),
                    m('.progress-bar.progress-bar-danger' + (ctrl.eventFilter === 'wiki' ? '.active.progress-bar-striped' : '.muted'), {style: {width: wikiEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.callLogs('wiki');
                        }, style: {color: 'white'}}, m('i.fa.fa-book'))
                    ),
                    (!(otherEvents == 100)) ?
                        m('.progress-bar.progress-bar-success.muted', {style: {width: otherEvents+'%'}}, m('i.fa.fa-plus')) :
                        m('.progress-bar', {style: {width: '100%', 'background-image': 'none', 'background-color': 'grey'}}, 'None')
                ]),
                m('',
                (ctrl.activityLogs() && (ctrl.activityLogs().length > 0))? ctrl.activityLogs().map(function(item){
                    return m('', [m('.fb-activity-item',
                        {style: {padding: '10px', paddingLeft: '5px', backgroundColor: '#f5f5f5', borderLeft: 'solid 5px ' + categoryColor(item.attributes.action)}}, [
                        m('span.text-muted.m-r-xs', item.attributes.formattableDate.local),
                        m.component(LogText,item)
                    ]), m('', {style: {padding: '5px'}})]);
                }) : m('p','No activity in this time range.')
                ),
                m('.text-center',
                m('.btn-group', [
                    m('button.btn.btn-primary' + (ctrl.page > 1 ? '' : '.disabled'), {onclick: function(){
                        ctrl.page--;
                        ctrl.getLogs()
                    }}, 'Previous'),
                    m('button.btn.btn-primary' + (ctrl.lastPage > ctrl.page ? '' : '.disabled'), {onclick: function(){
                        ctrl.page++;
                        ctrl.getLogs()
                    }}, 'Next')
                ]))
            ]))
        ]);
    }
};

module.exports = LogWrap;
