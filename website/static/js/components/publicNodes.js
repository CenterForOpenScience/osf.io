'use strict';

var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var $osf = require('js/osfHelpers');
var iconmap = require('js/iconmap');
var lodashFind = require('lodash.find');
var mHelpers = require('js/mithrilHelpers');
var Raven = require('raven-js');
var withPagination = require('js/components/pagination.js').withPagination;


var PROJECTS_PAGE_SIZE = 5;

var _buildUrl = function(page, user, nodeType) {
    var userFieldSet = ['family_name', 'full_name', 'given_name'];
    var nodeFieldSet = ['title', 'category', 'parent', 'public', 'contributors'];

    var query = {
        'page[size]': PROJECTS_PAGE_SIZE,
        'page': page || 1,
        'embed': ['contributors'],
        'version': '2.5',
        'fields[users]': userFieldSet.join(',')
    };

    var urlToReturn = $osf.apiV2Url('users/' + user +  '/nodes/', { query: query});
    if (nodeType === 'preprints') {
        urlToReturn = $osf.apiV2Url('users/' + user +  '/preprints/', { query: query});
    }
    else {
        query['filter[parent]'] = 'null';
        query['fields[nodes]'] = nodeFieldSet.join(',');
        query['fields[public]'] = 'true';
        if (nodeType === 'registrations'){
            urlToReturn = $osf.apiV2Url('users/' + user +  '/registrations/', { query: query});
        }
    }

    return urlToReturn;
};

var _getNextItems = function(ctrl, url, updatePagination) {
    if(ctrl.requestPending()) {
        return;
    }

    ctrl.publicProjects([]);
    ctrl.requestPending(true);

    var promise = m.request({
        method : 'GET',
        url : url,
        background : true,
        config: mHelpers.apiV2Config({withCredentials: window.contextVars.isOnRootDomain})
    });

    promise.then(
        function(result) {
            ctrl.requestPending(false);
            ctrl.publicProjects(result.data);
            updatePagination(result, url);
            m.redraw();
            return promise;
        }, function(xhr, textStatus, error) {
            ctrl.failed = true;
            ctrl.requestPending(false);
            m.redraw();
            Raven.captureMessage('Error retrieving projects', {extra: {url: url, textStatus: textStatus, error: error}});
        }
    );
};



function _formatContributors(item) {

    var contributorList = item.embeds.contributors.data;
    var totalContributors = item.embeds.contributors.meta.total;
    var isContributor = lodashFind(contributorList, ['id', window.contextVars.currentUser.id]);

    if (!isContributor) {
        // only show bibliographic contributors
        contributorList = contributorList.filter(function (contrib) {
            return contrib.attributes.bibliographic;
        });
        totalContributors = item.embeds.contributors.meta.total_bibliographic;
    }

    return contributorList.map(function (person, index, arr) {
        var names = $osf.extractContributorNamesFromAPIData(person);
        var name;
        var familyName = names.familyName;
        var givenName = names.givenName;
        var fullName = names.fullName;

        if (familyName) {
            name = familyName;
        } else if(givenName){
            name = givenName;
        } else if(fullName){
            name = fullName;
        } else {
            name = 'A contributor';
        }
        var comma;
        if (index === 0) {
            comma = '';
        } else if (index === totalContributors - 1) {
            comma = ' & ';
        } else {
            comma = ', ';
        }
        if (index > 3) {
            return;
        }
        if (index === 3) {
            // We already show names of the two
            return m('span', {}, [
                ' & ',
                m('a', {'href': item.links.html}, (totalContributors - 3) + ' more')
            ]);
        }
        return m('span', {}, [
            comma,
            m('a', {'href': person.embeds.users.data.links.html}, name)
        ]);
    });
}

var PublicNode = {

    controller: function(options) {
        var self = this;
        self.node = options.node;
        self.nodeType = options.nodeType;

        self.icon =  iconmap.projectComponentIcons[self.node.attributes.category];
    },

    view: function(ctrl)  {

        return m('div', [
            m('li.project list-group-item list-group-item-node cite-container', [
                m('h4.list-group-item-heading', [
                    m('span.component-overflow.f-w-lg', {style: 'line-height: 1.5;', width: '100%'}, [
                        m('span.project-statuses-lg'),
                        m('span', {
                            class: ctrl.nodeType === 'preprints' ? 'fa fa-file-o' : ctrl.icon,
                            style: 'padding-right: 5px;'
                        }, ''),
                        m('a', {'href': ctrl.node.links.html}, $osf.decodeText(ctrl.node.attributes.title))
                    ])
                ]),
                m('div.project-authors', {}, _formatContributors(ctrl.node)),
            ])
        ]);
    }
};

var PublicNodes = {

    controller: function(options) {
        var self = this;
        self.failed = false;
        self.user = options.user._id;
        self.isProfile = options.user.is_profile;
        self.nodeType = options.nodeType;

        self.publicProjects = m.prop([]);
        self.requestPending = m.prop(false);

        self.getCurrentProjects = function _getCurrentProjects (page){
            if(!self.requestPending()) {
                var url = _buildUrl(page, self.user, self.nodeType);
                return _getNextItems(self, url, options.updatePagination);
            }
        };

        self.getCurrentProjects();
    },

    view : function (ctrl) {
        var OSF_SUPPORT_EMAIL = $osf.osfSupportEmail();
        var nodeInfo = ctrl.nodeType ==='preprints' ? ctrl.nodeType : 'public '+ ctrl.nodeType ;

        var helpText = 'make your project public';
        var helpUrl = 'http://help.osf.io/m/gettingstarted/l/524048-control-your-privacy-settings';
        if (ctrl.nodeType === 'preprints'){
            helpText = 'share a preprint';
            helpUrl = 'http://help.osf.io/m/preprints/l/627729-share-a-preprint';
        }
        else if (ctrl.nodeType === 'registrations'){
            helpText = 'register a project';
            helpUrl = 'http://help.osf.io/m/registrations/l/524205-register-your-project';
        }

        return m('ul.list-group m-md', [
            // Error message if the request fails
            ctrl.failed ? m('p', [
                'Unable to retrieve ' + nodeInfo + ' at this time. Please refresh the page or contact ',
                m('a', {'href': 'mailto:' + OSF_SUPPORT_EMAIL}, OSF_SUPPORT_EMAIL),
                ' if the problem persists.'
            ]) :

            // Show laoding icon while there is a pending request
            ctrl.requestPending() ?  m('.ball-pulse.ball-scale-blue.text-center', [m(''), m(''), m('')]) :

            // Display each project
            [
                ctrl.publicProjects().length !== 0 ? ctrl.publicProjects().map(function(node) {
                    return m.component(PublicNode, {nodeType: ctrl.nodeType, node: node});
                }) : ctrl.isProfile ?
                    m('div.help-block', {}, [
                        'You have no ' + nodeInfo + '.',
                        m('p', {}, [
                            'Find out how to ',
                            m('a', {'href': helpUrl, 'target': '_blank'}, helpText),
                            '.'
                        ])
                    ])
                : m('div.help-block', {}, 'This user has no ' + nodeInfo + '.')

            ]
        ]);

    }
};

var PaginationWrapper = withPagination({
    buildUrl: _buildUrl,
    getNextItems: _getNextItems
});

PublicNodes = new PaginationWrapper(PublicNodes);


module.exports = {
    PublicNodes: PublicNodes
};
