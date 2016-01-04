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
        self.getMyNodes = function () {
            var url = $osf.apiV2Url('users/me/nodes/', { query : { 'embed': 'contributors'}});
            var promise = m.request({method: 'GET', url : url, config : xhrconfig});
            promise.then(function(result){
                //console.log(result)
                result.data.forEach(function(node){
                    self.nodes.push(node)
                })
            });
            return promise;
        };
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
        self.getMyNodes()

    },
    view : function(ctrl) {
        console.log(ctrl.nodes);
        return m('table', [
            m('tr', [
                m('th', 'Name'),
                m('th', 'Contributors'),
                m('th', 'Modified')
            ]),
            ctrl.nodes.map(function(n){
                return m('tr', [
                  m('td', n.attributes.title),
                    m('td', ctrl.getContributors(n)),
                    m('td', n.attributes.date_modified)
                ])
            })
        ]);
    }
};

module.exports = quickSearchProject;

