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
        self.page = 1;

        self.getLogs = function () {
            var query = {
                'embed': ['nodes', 'user', 'linked_node', 'template_node'],
                'page': self.page
            };
            if (self.eventFilter) {
                query['filter[action]'] = self.eventFilter;
            }
            var url = $osf.apiV2Url('users/' + self.userId + '/node_logs/', { query : query});
            var promise = m.request({method : 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                result.data.map(function(log){
                    log.attributes.formattableDate = new $osf.FormattableDate(log.attributes.date);
                });
                self.activityLogs(result.data);
                self.totalEvents = result.links.meta.total;
                self.eventNumbers = result.links.meta.aggregates;
                self.lastPage = (result.links.meta.total / result.links.meta.per_page | 0) + 1;
            });
            return promise;
        };
        self.getLogs(self.userId);
    },
    view: function(ctrl, args){
        var fileEvents = (ctrl.eventNumbers.files/ctrl.totalEvents)*100 | 0;
        var commentEvents = (ctrl.eventNumbers.comments/ctrl.totalEvents)*100 | 0;
        var wikiEvents = (ctrl.eventNumbers.wiki/ctrl.totalEvents)*100 | 0;
        var nodeEvents = (ctrl.eventNumbers.nodes/ctrl.totalEvents)*100 | 0;
        var otherEvents = 100 - (fileEvents + commentEvents + wikiEvents + nodeEvents);
        return m('.panel.panel-default', [
            m('.panel-heading', 'Recent Activity'),
            m('.panel-body',
            m('.fb-activity-list.m-t-md', [
                m('.progress', [
                    m('.progress-bar.progress-bar-striped.active', {style: {width: fileEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = 'osf_storage_file_added,osf_storage_file_updated';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Files')
                    ),
                    m('.progress-bar.progress-bar-striped.active.progress-bar-warning', {style: {width: nodeEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = 'node_created,project_created';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Nodes')
                    ),
                    m('.progress-bar.progress-bar-striped.active.progress-bar-info', {style: {width: commentEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = 'comment_added';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Comments')
                    ),
                    m('.progress-bar.progress-bar-striped.active.progress-bar-danger', {style: {width: wikiEvents+'%'}},
                        m('a', {onclick: function(){
                            ctrl.eventFilter = 'wiki_updated';
                            ctrl.page = 1;
                            ctrl.getLogs();
                        }}, 'Wiki')
                    ),
                    m('.progress-bar.progress-bar-striped.active.progress-bar-success', {style: {width: otherEvents+'%'}}, 'Other')
                ]),
                ctrl.activityLogs() ? ctrl.activityLogs().map(function(item){
                    return m('.fb-activity-item', [
                        m('span.text-muted.m-r-xs', item.attributes.formattableDate.local),
                        m.component(LogText,item)
                    ]);
                }) : '',
                m('.btn-group', [
                    ctrl.page > 1 ?m('button.btn.btn-info', {onclick: function(){
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
}


$(document).ready(function() {
    m.mount(document.getElementById('recentActivityWidget'), m.component(LogWrap, {userId: window.contextVars.userId}));
});
