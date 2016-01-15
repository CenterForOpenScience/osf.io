/**
 * UI and function to quick search projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var nodeModule = require('js/quickProjectSearchPlugin');

// CSS
require('css/new-and-noteworthy-plugin.css');

// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var newAndNoteworthy = {
    controller: function() {
        var self = this;
        self.newNodes = m.prop([]);
        self.noteworthyNodes = m.prop([]);

        // Load new nodes
        var url = $osf.apiV2Url('nodes/', { query : { 'embed': 'contributors'}});
        var promise = m.request({method: 'GET', url : url, config: xhrconfig});
        promise.then(function(result){
            result.data.forEach(function(node){
                self.newNodes().push(node);
            });
            return promise
        });

        // Gets contrib full name for display
        self.getFullName = function(node) {
            return node.embeds.contributors.data[0].embeds.users.data.attributes.full_name
        };

        // Formats contrib names for display
        self.getContributors = function (node) {
            var numContributors = node.embeds.contributors.links.meta.total;
            if (numContributors === 1) {
                return self.getFullName(node)
            }
            else {
                return self.getFullName(node) + ' et al'
            }

        };


    },
    view : function(ctrl) {
        function nodeDisplay(node) {
            return m('div', {class: 'row'},
                m('div', {class: 'col-sm-12'},
                    m('h5', node.attributes.title),
                    m('h5', node.attributes.description),
                    m('h5', 'Contributors: ' + ctrl.getContributors(node))
                )
            )
        }

        function newProjectsTemplate () {
            return ctrl.newNodes().map(function(node){
                return nodeDisplay(node)
            })

        }
        function noteworthyProjectsTemplate() {
            return m('h1', 'Nodes')

        }
        return m('div', {class: 'container'}, [
            m('div', {class: 'row'}, m('div', {class: 'col-sm-12'}, m('h3', 'Discover Public Projects'))),
            m('div', {class: 'row'},
                m('div', {class: 'col-sm-6'}, [m('h4', 'New'), newProjectsTemplate() ]),
                m('div', {class: 'col-sm-6'}, [m('h4', 'Noteworthy', noteworthyProjectsTemplate())])
            )
        ])
    }
};

module.exports = newAndNoteworthy;

