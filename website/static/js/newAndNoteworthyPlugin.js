/**
 * New and Noteworthy Projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');

// CSS
require('css/quick-project-search-plugin.css');

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
            for (var i = 0; i <= 4; i++) {
                self.newNodes().push(result.data[i])
            }
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

         // Colors node div and changes cursor to pointer on hover
        self.mouseOver = function (node) {
            node.style.backgroundColor='#E0EBF3';
            node.style.cursor = 'pointer'
        };

        self.mouseOut = function (node) {
            node.style.backgroundColor='#fcfcfc'
        };

         // Onclick, directs user to project page
        self.nodeDirect = function(node) {
            location.href = '/'+ node.id
        };

        self.redirectToSearch = function() {
            location.href = '/search'
        }


    },
    view : function(ctrl) {
        function nodeDisplay(node) {
            return m('div', {class: 'row node-styling m-v-sm', onmouseover: function(){ctrl.mouseOver(this)}, onmouseout: function(){ctrl.mouseOut(this)}, onclick: function(){{ctrl.nodeDirect(node)}}},
                m('div', {class: 'col-sm-12'},
                    m('h5', m('em', node.attributes.title)),
                    m('h5', node.attributes.description),
                    m('div', m('h5', {class: 'contributors-bold f-w-xl'}, 'Contributors: '), ctrl.getContributors(node)
                    )
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

        function findMoreProjectsButton () {
            return m('button', {type:'button', class:'btn btn-default m-v-md', onclick: function(){
                ctrl.redirectToSearch()
            }}, 'Find more projects with advanced search')
        }

        return m('div', {class: 'container'}, [
            m('div', {class: 'row'},
                m('div', {class: 'col-sm-1'}),
                m('div', {class: 'col-sm-11'}, m('h3', 'Discover Public Projects'))),
            m('div', {class: 'row'}, m('div', {class:'col-sm-10 col-sm-offset-1'},
                m('div', {class: 'col-sm-6'}, [m('h4', 'New'), newProjectsTemplate() ]),
                m('div', {class: 'col-sm-6'}, [m('h4', 'Noteworthy', noteworthyProjectsTemplate())])
            )),
            m('div', {class: 'row'},
                m('div', {class: 'col-sm-1'}),
                m('div', {class: 'col-sm-10 text-center'}, findMoreProjectsButton()),
                m('div', {class: 'col-sm-1'})

            )
        ])
    }
};

module.exports = newAndNoteworthy;

