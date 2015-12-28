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
        self.today = new Date();
        self.page = 1;

        self.getLogs = function(init) {
            var query = {
                'embed': ['nodes', 'user', 'linked_node', 'template_node'],
                'page': self.page
            };
            if (self.eventFilter) {
                query['filter[action]'] = self.eventFilter;
            }
            if (init) {
                query['aggregate'] = 1;
            } else {
                var save = Number(self.dateEnd);
                query['filter[date][lte]'] = self.dateEnd.toISOString();
                self.dateEnd.setMonth(self.dateEnd.getMonth() - 1);
                query['filter[date][gte]'] = self.dateEnd.toISOString();
                self.dateEnd = new Date(save);
            }
            var url = $osf.apiV2Url('users/' + self.userId + '/node_logs/', { query : query});
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                });
                if (!init) {self.activityLogs(result.data)}
                if (init) {
                    self.totalEvents = result.links.meta.total;
                    self.eventNumbers = result.links.meta.aggregates;
                    self.lastDay = new Date(result.data[0].attributes.date);
                    self.dateEnd = self.lastDay;
                    self.firstDay = new Date(result.links.meta.last_log_date);
                }
                self.lastPage = (result.links.meta.total / result.links.meta.per_page | 0) + 1;
            });
            return promise;
        };
        self.getLogs(true);
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
                $
                $("#recentActivitySlider").slider({
                    min: Number(ctrl.firstDay),
                    max: Number(ctrl.today),
                    value: Number(ctrl.dateEnd),
                    range: true,
                    stop: function (event, ui) {
                        ctrl.page = 1;
                        ctrl.dateEnd = new Date(ui.value);
                        ctrl.getLogs();
                    }
                });
            }
            else {
                $( "#recentActivitySlider" ).slider( "value", Number(ctrl.dateEnd), Number(ctrl.dateEnd) - 2.628e+9);
            }
        };
        return m('.panel.panel-default', [
            m('.panel-heading', 'Recent Activity'),
            m('.panel-body',
            m('.fb-activity-list.m-t-md', [
                m('#recentActivitySlider', {style: {margin: '10px'}, config: addSlider}),
                m('.progress', [
                    m('.progress-bar' + (ctrl.eventFilter === 'file' ? '.active.progress-bar-striped' : ''), {style: {width: fileEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = ctrl.eventFilter === 'file' ? false : 'file';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Files')
                    ),
                    m('.progress-bar.progress-bar-warning' + (ctrl.eventFilter === 'project' ? '.active.progress-bar-striped' : ''), {style: {width: nodeEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = ctrl.eventFilter === 'project' ? false : 'project';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Nodes')
                    ),
                    m('.progress-bar.progress-bar-info' + (ctrl.eventFilter === 'comment' ? '.active.progress-bar-striped' : ''), {style: {width: commentEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = ctrl.eventFilter === 'comment' ? false : 'comment';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Comments')
                    ),
                    m('.progress-bar.progress-bar-danger' + (ctrl.eventFilter === 'wiki' ? '.active.progress-bar-striped' : ''), {style: {width: wikiEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = ctrl.eventFilter === 'wiki' ? false : 'wiki';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Wiki')
                    ),
                    m('.progress-bar.progress-bar-success', {style: {width: otherEvents+'%'}}, 'Other')
                ]),
                ctrl.activityLogs() ? ctrl.activityLogs().map(function(item){

                    return m('.fb-activity-item', [
                        m('span.text-muted.m-r-xs', item.attributes.formattableDate.local),
                        m.component(LogText,item)
                    ]);
                }) : '',
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
