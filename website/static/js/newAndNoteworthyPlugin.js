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


var NewAndNoteworthy = {
    controller: function() {
        var self = this;
        self.newAndNoteworthyNodes = m.prop([]);
        self.popularNodes = m.prop([]);
        self.contributorsMapping = {};
        self.SHOW_TOTAL = 5;

        // Load new and noteworthy nodes
        var newAndNoteworthyUrl = $osf.apiV2Url('nodes/' + window.contextVars.newAndNoteworthy + '/node_links/', {});
        var newAndNoteworthyPromise = m.request({method: 'GET', url: newAndNoteworthyUrl, config: xhrconfig});
        newAndNoteworthyPromise.then(function(result){
            var numNew = Math.min(result.data.length, self.SHOW_TOTAL);
            for (var l = 0; l < numNew; l++) {
                self.newAndNoteworthyNodes().push(result.data[l]);
                self.fetchContributors(result.data[l]);
            }
        });

        // Load popular nodes
        var popularUrl = $osf.apiV2Url('nodes/' + window.contextVars.popular + '/node_links/', {});
        var popularPromise = m.request({method: 'GET', url: popularUrl, config: xhrconfig});
        popularPromise.then(function(result){
            var numPopular = Math.min(result.data.length, self.SHOW_TOTAL);
            for (var l = 0; l < numPopular; l++) {
                self.popularNodes().push(result.data[l]);
                self.fetchContributors(result.data[l]);
            }
        });

        // Additional API call to fetch node link contributors
        self.fetchContributors = function(nodeLink) {
            var url = nodeLink.embeds.target_node.data.relationships.contributors.links.related.href;
            var promise = m.request({method: 'GET', url : url, config: xhrconfig});
            promise.then(function(result){
                var contribNames = [];
                result.data.forEach(function (contrib){
                    contribNames.push(contrib.embeds.users.data.attributes.family_name);
                });
                var numContrib = result.links.meta.total;
                var nodeId = nodeLink.id;
                self.contributorsMapping[nodeId] = [contribNames, numContrib];
            });
        };

        // Gets contrib family name for display
        self.getFamilyName = function(i, node) {
            return self.contributorsMapping[node.id][0][i];
        };

        self.addToolTip = function(line) {
            var $line = $(line);
            if (line.offsetWidth < line.scrollWidth) {
                $line.tooltip('show');
            }
        };
    },
    view : function(ctrl) {
        function nodeDisplay(node) {
            var description = node.embeds.target_node.data.attributes.description;
            var title = node.embeds.target_node.data.attributes.title;
            var contributors = $osf.contribNameFormat(node, ctrl.contributorsMapping[node.id][1], ctrl.getFamilyName);

            return m('div.node-styling.noteworthy-spacing', {'class': 'row', onclick: function(){
                location.href = '/' + node.embeds.target_node.data.id;}
            },
                m('div', {'class': 'col-sm-12'},
                    m('h5.prevent-overflow', {'data-title': title, 'data-location': 'top', onmouseover: function(){ctrl.addToolTip(this);}},
                        m('em', title)),
                    m('h5.prevent-overflow', {'data-title': description, 'data-location': 'top', onmouseover: function(){ctrl.addToolTip(this);}},
                        description ?  description : m('div.blank-line')),
                    m('h5.prevent-overflow',  {'data-title': contributors, 'data-location': 'top', onmouseover: function(){ctrl.addToolTip(this);}},
                        m('span.f-w-xl', 'Contributors: '),
                            m('span', contributors ))
                )
            );
        }

        function newAndNoteworthyProjectsTemplate () {
            return ctrl.newAndNoteworthyNodes().map(function(node){
                return nodeDisplay(node);
            });
        }

        function popularProjectsTemplate () {
            return ctrl.popularNodes().map(function(node){
                return nodeDisplay(node);
            });
        }

        function findMoreProjectsButton () {
            return m('a.btn.btn-default.m-v-lg', {type:'button', href:'/search'}, 'Find more projects with advanced search');
        }

        return m('div', {'class': 'container'}, [
            m('div', {'class': 'row'},
                m('div', {'class': 'col-md-10 col-md-offset-1'},
                    m('div', {'class': 'col-sm-12'}, m('h3', 'Discover Public Projects')))),

            m('div', {'class': 'row'},
                m('div', {'class': 'col-md-10 col-md-offset-1'},
                    m('div', {'class': 'col-sm-6 col-xs-12'}, m('h4', 'New and Noteworthy'), newAndNoteworthyProjectsTemplate()),
                    m('div', {'class': 'col-sm-6 col-xs-12'}, m('h4', 'Most Popular'), popularProjectsTemplate ())
            )),

            m('div', {'class': 'row'},
                m('div.text-center', {'class': 'col-sm-12'}, findMoreProjectsButton())
            )
        ]);
    }
};

module.exports = NewAndNoteworthy;

