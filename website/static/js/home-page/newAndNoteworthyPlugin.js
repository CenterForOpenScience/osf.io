/**
 * New and Noteworthy Projects
 */

var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var Raven = require('raven-js');
var lodashGet = require('lodash.get');


// CSS
require('css/new-and-noteworthy-plugin.css');
require('loaders.css/loaders.min.css');


// XHR config for apiserver connection
var xhrconfig = function(xhr) {
    xhr.withCredentials = true;
};


var NewAndNoteworthy = {
    controller: function() {
        var self = this;
        self.newAndNoteworthyNodes = m.prop([]); // New and noteworthy nodes list
        self.popularNodes = m.prop([]); // Most popular nodes list
        self.contributorsMapping = {}; // Dictionary mapping node id to some of the contrib names and the contrib total.
        self.SHOW_TOTAL = 5; // Number of new and noteworthy projects displayed in each column
        self.errorLoading = m.prop(false);  // True if error retrieving projects or contributors.
        self.someDataLoaded = m.prop(false);
        self.someContributorsLoaded = m.prop(false);

        // Switches errorLoading to true
        self.requestError = function(result){
            self.errorLoading = m.prop(true);
            Raven.captureMessage('Error loading new and noteworthy projects on home page.', {
                extra: { requestReturn: result }
            });
        };

        // Load new and noteworthy nodes
        var newAndNoteworthyUrl = $osf.apiV2Url('nodes/' + window.contextVars.newAndNoteworthy + '/node_links/', {});
        var newAndNoteworthyPromise = m.request({method: 'GET', url: newAndNoteworthyUrl, config: xhrconfig, background: true});
        newAndNoteworthyPromise.then(function(result){
            var numNew = Math.min(result.data.length, self.SHOW_TOTAL);
            for (var l = 0; l < numNew; l++) {
                var data = result.data[l];
                if (lodashGet(data, 'embeds.target_node.data', null)) {
                    self.newAndNoteworthyNodes().push(result.data[l]);
                    self.fetchContributors(result.data[l]);
                }
            }
            self.someDataLoaded(true);
        }, function _error(result){
            self.requestError(result);
            m.redraw();
        });

        // Load popular nodes
        var popularUrl = $osf.apiV2Url('nodes/' + window.contextVars.popular + '/node_links/', {});
        var popularPromise = m.request({method: 'GET', url: popularUrl, config: xhrconfig, background: true});
        popularPromise.then(function(result){
            var numPopular = Math.min(result.data.length, self.SHOW_TOTAL);
            for (var l = 0; l < numPopular; l++) {
                var data = result.data[l];
                if (lodashGet(data, 'embeds.target_node.data', null)) {
                    self.popularNodes().push(result.data[l]);
                    self.fetchContributors(result.data[l]);
                }
            }
            self.someDataLoaded(true);
        }, function _error(result){
            self.requestError(result);
            m.redraw();
        });

        // Additional API call to fetch node link contributors
        self.fetchContributors = function(nodeLink) {
            var url = lodashGet(nodeLink, 'embeds.target_node.data.relationships.contributors.links.related.href', null);
            var promise = m.request({method: 'GET', url : url, config: xhrconfig});
            promise.then(function(result){
                var contribNames = [];
                result.data.forEach(function (contrib){
                    if (contrib.attributes.unregistered_contributor) {
                        contribNames.push(contrib.attributes.unregistered_contributor);
                    }
                    else if (contrib.embeds.users.data){
                        contribNames.push($osf.findContribName(contrib.embeds.users.data.attributes));
                    }
                    else if (contrib.embeds.users.errors) {
                        contribNames.push($osf.findContribName(contrib.embeds.users.errors[0].meta));
                    }

                });
                self.someContributorsLoaded(true);
                var numContrib = result.links.meta.total;
                var nodeId = nodeLink.id;
                self.contributorsMapping[nodeId] = {'names': contribNames, 'total': numContrib};
            }, function _error(result){
                self.requestError(result);
            });
        };

        // Gets contrib family name for display
        self.getFamilyName = function(i, node) {
            if (!(Boolean(self.contributorsMapping) && Boolean(self.contributorsMapping[node.id])))  {
                return null;
            }
            return self.contributorsMapping[node.id].names[i];
        };

    },
    view : function(ctrl) {
        if (ctrl.errorLoading()) {
            return m('p.text-center.m-v-lg', 'Error loading projects. Please refresh the page. Contact support@osf.io for further assistance.');
        }

        if (!ctrl.someDataLoaded()) {
            return m('.loader-inner.ball-scale.text-center.m-v-xl', m(''));
        }

        function newAndNoteworthyProjectsTemplate () {
            return ctrl.newAndNoteworthyNodes().map(function(node){
                return m.component(NoteworthyNodeDisplay, {
                    node : node,
                    getFamilyName: ctrl.getFamilyName,
                    contributorsMapping: ctrl.contributorsMapping
                });
            });
        }

        function popularProjectsTemplate () {
            return ctrl.popularNodes().map(function(node){
                return m.component(NoteworthyNodeDisplay, {
                    node : node,
                    getFamilyName: ctrl.getFamilyName,
                    contributorsMapping: ctrl.contributorsMapping
                });
            });
        }

        function findMoreProjectsButton () {
            return m('a.btn.btn-default.m-v-lg', {type:'button', href:'/search', onclick: function() {
                $osf.trackClick('discoverPublicProjects', 'navigate', 'navigate-to-search-for-more-projects');
            }}, 'Search for more projects');
        }

        if (ctrl.someContributorsLoaded()){
            return m('',[
                m('.row',[
                    m('.col-xs-12.col-md-6', m('.public-projects-box.', m('h4.m-b-md','New and Noteworthy'), newAndNoteworthyProjectsTemplate())),
                    m('.col-xs-12.col-md-6', m('.public-projects-box.', m('h4.m-b-md','Most Popular'), popularProjectsTemplate ()))
                ]),
                m('.row', m('.text-center.col-sm-12', findMoreProjectsButton()))
        ]);

        }
        return m('');
    }
};


var NoteworthyNodeDisplay = {
    controller: function() {
        var self = this;
        self.addToolTip = function(line) {
            var $line = $(line);
            if (line.offsetWidth < line.scrollWidth) {
                $line.tooltip('show');
            }
        };
    },
    view: function(ctrl, args) {
        var description = args.node.embeds.target_node.data.attributes.description;
        var tooltipDescription = description ? description.split(' ').splice(0,30).join(' ') + '...' : '';
        var title = args.node.embeds.target_node.data.attributes.title;
        var numContrib = args.contributorsMapping[args.node.id] ? args.contributorsMapping[args.node.id].total : 0;
        var contributors = $osf.contribNameFormat(args.node, numContrib, args.getFamilyName);
        var destination = '/' + args.node.embeds.target_node.data.id;

        return m('a', {href: destination, onclick: function() {
            $osf.trackClick('discoverPublicProjects', 'navigate', 'navigate-to-specific-project');
        }}, m('.public-projects-item',[
            m('h5', title),
            m('span.prevent-overflow', m('i', 'by ' + contributors)),
            description ? m('p.prevent-overflow', {'data-title': tooltipDescription, 'data-location': 'top', onmouseover: function(){
                ctrl.addToolTip(this);
            }}, description) : ''
        ]));
    }
};

module.exports = NewAndNoteworthy;

