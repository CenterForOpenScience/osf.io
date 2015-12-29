var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var LogText = require('js/logTextParser');

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
        self.dateEnd = new Date();
        self.dateBegin = new Date();
        self.today = new Date();
        self.page = 1;

        self.getLogs = function(init, reset) {
            var query = {
                'embed': ['nodes', 'user', 'linked_node', 'template_node'],
                'page': self.page,
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
                    self.lastDay = new Date(result.data[0].attributes.date);
                    self.dateEnd = self.lastDay;
                    self.lastDay.setMonth(self.lastDay.getMonth() - 1);
                    self.dateBegin = self.lastDay;
                    self.firstDay = new Date(result.links.meta.last_log_date);
                }
                if (init || reset){
                    self.totalEvents = result.links.meta.total;
                    self.eventNumbers = result.links.meta.aggregates;
                }
                if (!init) {self.activityLogs(result.data)}
                self.lastPage = (result.links.meta.total / result.links.meta.per_page | 0) + 1;
            });
            return promise;
        };
        self.getLogs(true, false);
        self.getLogs();
    },
    view: function(ctrl, args){
        var fileEvents = (ctrl.eventNumbers.files/ctrl.totalEvents)*100 | 0;
        var commentEvents = (ctrl.eventNumbers.comments/ctrl.totalEvents)*100 | 0;
        var wikiEvents = (ctrl.eventNumbers.wiki/ctrl.totalEvents)*100 | 0;
        var nodeEvents = (ctrl.eventNumbers.nodes/ctrl.totalEvents)*100 | 0;
        var otherEvents = 100 - (fileEvents + commentEvents + wikiEvents + nodeEvents);
        var addSlider = function(ele, isInitialized){
            if (!isInitialized) {
                $("#recentActivitySlider").slider({
                    min: Number(ctrl.firstDay),
                    max: Number(ctrl.today),
                    values: [Number(ctrl.dateBegin), Number(ctrl.dateEnd)],
                    range: true,
                    stop: function (event, ui) {
                        ctrl.page = 1;
                        ctrl.dateBegin = new Date(ui.values[0]);
                        ctrl.dateEnd = new Date(ui.values[1]);
                        ctrl.getLogs(false, true);
                    },
                    slide: function (event, ui) {

                    }
                });
            }
            else {
                $( "#recentActivitySlider" ).slider( 'option', "values", [Number(ctrl.dateBegin),  Number(ctrl.dateEnd)]);
            }
        };
        return m('.panel.panel-default', [
            m('.panel-heading', 'Recent Activity'),
            m('.panel-body',
            m('.fb-activity-list.m-t-md', [
                m('#recentActivitySlider', {style: {margin: '10px'}, config: addSlider}),
                m('.progress', [
                    m('.progress-bar' + (ctrl.eventFilter === 'file' ? '.active.progress-bar-striped' : '.muted'), {style: {width: fileEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = ctrl.eventFilter === 'file' ? false : 'file';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Files')
                    ),
                    m('.progress-bar.progress-bar-warning' + (ctrl.eventFilter === 'project' ? '.active.progress-bar-striped' : '.muted'), {style: {width: nodeEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = ctrl.eventFilter === 'project' ? false : 'project';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Nodes')
                    ),
                    m('.progress-bar.progress-bar-info' + (ctrl.eventFilter === 'comment' ? '.active.progress-bar-striped' : '.muted'), {style: {width: commentEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = ctrl.eventFilter === 'comment' ? false : 'comment';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Comments')
                    ),
                    m('.progress-bar.progress-bar-danger' + (ctrl.eventFilter === 'wiki' ? '.active.progress-bar-striped' : '.muted'), {style: {width: wikiEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = ctrl.eventFilter === 'wiki' ? false : 'wiki';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Wiki')
                    ),
                    m('.progress-bar.progress-bar-success.muted', {style: {width: otherEvents+'%'}}, 'Other')
                ]),
                ctrl.activityLogs() ? ctrl.activityLogs().map(function(item){

                    return m('.fb-activity-item', [
                        m('span.text-muted.m-r-xs', item.attributes.formattableDate.local),
                        m.component(LogText,item)
                    ]);
                }) : m('p','No activity in this time range.'),
                m('.btn-group', [
                    ctrl.page > 1 ? m('button.btn.btn-info', {onclick: function(){
                        ctrl.page--;
                        ctrl.getLogs()
                    }}, 'Previous') : '',
                    ctrl.lastPage > ctrl.page ? m('button.btn.btn-info', {onclick: function(){
                        ctrl.page++;
                        ctrl.getLogs()
                    }}, 'Next') : ''
                ])
            ]))
        ]);
    }
};


$(document).ready(function() {
    m.mount(document.getElementById('recentActivityWidget'), m.component(LogWrap, {userId: window.contextVars.userId}));
});
