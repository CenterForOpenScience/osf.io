/**
 * UI and function to quick search projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var quickSearchProject = {
    controller: function() {
        var self = this;
        self.nodes = [];
        self.displayedNodes = [];

        // Load node list
        var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': 'contributors', 'page[size]': 100}});
        var promise = m.request({method: 'GET', url : url, config : xhrconfig});
        promise.then(function(result){
            result.data.forEach(function(node){
                self.nodes.push(node);
            })
        });

        self.getFamilyName = function(i, node) {
            return node.embeds.contributors.data[i].embeds.users.data.attributes.family_name
        };
        self.getContributors = function (node) {
            var numContributors = node.embeds.contributors.links.meta.total;
            if (numContributors === 1) {
                return self.getFamilyName(0, node)
            }
            else if (numContributors == 2) {
                return self.getFamilyName(0, node) + ' and ' +
                        self.getFamilyName(1, node)
            }
            else {
                return self.getFamilyName(0, node) + ', ' +
                        self.getFamilyName(1, node) + ', ' +
                        self.getFamilyName(2, node) + ' and ' +
                    (numContributors - 3) + ' others'
            }

        };
        self.loadUpToTen = function () {
            requested = self.nodes.splice(0, 10);
            for (i = 0; i < requested.length; i++) {
                self.displayedNodes.push(requested[i])
            }
            return self.displayedNodes
        };

        self.formatDate = function (node) {
            return new $osf.FormattableDate(node.attributes.date_modified).local
        }

    },
    view : function(ctrl) {
        function projectView(project) {
            return m('tr', [
                m('td', project.attributes.title),
                m('td', ctrl.getContributors(project)),
                m('td', ctrl.formatDate(project))
            ])
        }

        return m('div', [
            m('table', [
                m('tr', [
                    m('th', 'Name'),
                    m('th', 'Contributors'),
                    m('th', 'Modified')
                ]),
                ctrl.loadUpToTen().map(function(n){
                    return projectView(n)
                }),
                m('button', { onclick: function() {
                    ctrl.loadUpToTen() }
                }, 'Add more')
            ])
        ])
    }
};

module.exports = quickSearchProject;

