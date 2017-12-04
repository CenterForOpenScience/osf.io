'use strict';

var m = require('mithril'); // exposes mithril methods, useful for redraw etc.
var $osf = require('js/osfHelpers');
var iconmap = require('js/iconmap');
var lodashFind = require('lodash.find');
var mHelpers = require('js/mithrilHelpers');
var Raven = require('raven-js');

var withPagination = require('js/components/pagination').withPagination;

var QUICKFILES_PAGE_SIZE = 10;


var _buildUrl = function(page, user) {

    var query = {
        'page[size]': QUICKFILES_PAGE_SIZE,
        'page': page || 1,
        'version': '2.2',
    };

    return $osf.apiV2Url('users/' + user +  '/quickfiles/', { query: query});
};


var _getNextItems = function(ctrl, url, updatePagination) {
    if(ctrl.requestPending()) {
        return;
    }

    ctrl.quickFiles([]);
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
            ctrl.quickFiles(result.data);
            updatePagination(result, url);
            m.redraw();
            return promise;
        }, function(xhr, textStatus, error) {
            ctrl.failed = true;
            ctrl.requestPending(false);
            m.redraw();
            Raven.captureMessage('Error retrieving quickfiles', {
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        }
    );
};


var QuickFile = {

    controller: function(options) {
        var self = this;
        self.file = options.file;
        self.icon =  iconmap.file;
    },

    view: function(ctrl)  {
        var viewBase = window.location.origin + '/quickfiles';
        var viewUrl = ctrl.file.attributes.guid ? viewBase + '/' + ctrl.file.attributes.guid : viewBase + ctrl.file.attributes.path;
        return m('div', [
            m('li.project list-group-item list-group-item-node cite-container', [
                m('h4.list-group-item-heading', [
                    m('span.component-overflow.f-w-lg', {style: {lineHeight: 1.5, width: '100%'}}, [
                        m('span.col-md-8.project-statuses-lg', [
                            m('span', {class: ctrl.icon, style: 'padding-right: 5px;'}, ''),
                            m('a', {'href': viewUrl,
                                onclick : function () {
                                    $osf.trackClick('QuickFiles', 'view', 'view-quickfile-from-profile-page');
                                }
                            }, ctrl.file.attributes.name),
                        ])
                    ])
                ])
            ])
        ]);
    }
};

var QuickFiles = {

    controller: function (options) {
        var self = this;
        self.failed = false;
        self.user = options.user._id;
        self.isProfile = options.user.is_profile;

        self.quickFiles = m.prop([]);
        self.requestPending = m.prop(false);

        self.getCurrentQuickFiles = function _getCurrentQuickFiles(page) {
            if (!self.requestPending()) {
                var url = _buildUrl(page, self.user);
                return _getNextItems(self, url, options.updatePagination);
            }
        };
        self.getCurrentQuickFiles();
    },

    view: function (ctrl) {

        return m('ul.list-group m-md', [
            // Error message if the request fails
            ctrl.failed ? m('p', [
                    'Unable to retrieve quickfiles at this time. Please refresh the page or contact ',
                    m('a', {'href': 'mailto:support@osf.io'}, 'support@osf.io'),
                    ' if the problem persists.'
                ]) :

            // Show laoding icon while there is a pending request
            ctrl.requestPending() ?  m('.ball-pulse.ball-scale-blue.text-center', [m(''), m(''), m('')]) :

            // Display each quickfile
            [
                ctrl.quickFiles().length !== 0 ? ctrl.quickFiles().map(function(file) {
                    return m.component(QuickFile, {file: file});
                }) : ctrl.isProfile ?
                    m('div.help-block', {}, 'You have no public quickfiles')
                : m('div.help-block', {}, 'This user has no public quickfiles.')
            ]
        ]);
    }
};

var PaginationWrapper = withPagination({
    buildUrl: _buildUrl,
    getNextItems: _getNextItems
});

QuickFiles = new PaginationWrapper(QuickFiles);


module.exports = {
    QuickFiles: QuickFiles
};
