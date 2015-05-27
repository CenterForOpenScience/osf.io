var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

var util = require('./util.js');


// Helper for filtering
function TRUTHY(item) {
    return !!item; //Force cast to a bool
}


var FileRevisionsTable = {
    controller: function(file, node) {
        var self = this;
        self.node = node;
        self.file = file;
        self.loaded = false;
        self.revisions = [];
        self.errorMessage = undefined;

        self.hasUser = true;
        self.hasDate = self.provider !== 'dataverse';

        self.currentRevision = 0;

        self.reload = function() {
            $.ajax({
                dataType: 'json',
                url: self.file.urls.revisions,
                beforeSend: $osf.setXHRAuthorization
            }).done(function(response) {
                m.startComputation();
                self.revisions = response.data.map(FileRevisionsTable.postProcessRevision.bind(this, self.file, self.node));
                self.loaded = true;
                self.hasUser = self.revisions[0] && self.revisions[0].extra && self.revisions[0].extra.user;
                m.endComputation();
            }).fail(function(response) {
                // self.versioningSupported(false);
                // var err = response.responseJSON ?
                //     response.responseJSON.message || 'Unable to fetch versions' :
                //     'Unable to fetch versions';

                // self.errorMessage(err);

                // if (self.file.provider === 'figshare') {
                //     // Hack for Figshare
                //     // only figshare will error on a revisions request
                //     // so dont allow downloads and set a fake current version
                //     $.ajax({
                //         method: 'GET',
                //         url: self.urls.metadata,
                //         beforeSend: $osf.setXHRAuthorization
                //     }).done(function(resp) {
                //         self.editable(resp.data.extra.canDelete);
                //     }).fail(function(xhr) {
                //         self.editable(false);
                //     });
                // }

                // self.currentVersion({
                //     osfViewUrl: '',
                //     osfDownloadUrl: '?action=download',
                //     download: function() {
                //         window.location = self.urls.download + '&' + $.param({displayName: self.file.name});
                //         return false;
                //     }
                // });
            });
        };

        self.getTableHead = function() {
            return m('thead', [
                m('tr', [
                    m('th', 'Version ID'),
                    self.hasDate ? m('th', 'Date') : false,
                    self.hasUser ? m('th', 'User') : false,
                    m('th[colspan=2]', 'Download'),
                ].filter(TRUTHY))
            ]);
        };

        self.makeTableRow = function(revision, index) {
            var isCurrent = index === self.currentRevision;

            return m('tr' + (isCurrent ? '.active' : ''), [
                m('td',  isCurrent ?
                  revision.displayVersion :
                  m('a', {href: revision.osfViewUrl}, revision.displayVersion)
                ),
                self.hasDate ? m('td', revision.displayDate) : false,
                self.hasUser ?
                    m('td', revision.extra.user.url ?
                        m('a', {href: revision.extra.user.url}, revision.extra.user.name) :
                        revision.extra.user.name
                    ) : false,
                m('td', revision.extra.downloads > -1 ? m('.badge', revision.extra.downloads) : ''),
                m('td',
                  m('a.btn.btn-primary.btn-sm.file-download', {
                        href: revision.osfDownloadUrl,
                        onclick: function() {
                            window.location = revision.waterbutlerDownloadUrl;
                            return false;
                        }
                    }, m('i.fa.fa-download'))
                ),
            ].filter(TRUTHY));
        };

        self.reload();
    },
    view: function(ctrl) {
        if (!ctrl.loaded) return util.Spinner;

        return m('table.table', [
            ctrl.getTableHead(),
            m('tbody', ctrl.revisions.map(ctrl.makeTableRow))
        ]);
    },
    postProcessRevision: function(file, node, revision, index) {
        var options = {};
        var urlParams = $osf.urlParams();

        if (urlParams.branch !== undefined) {
            options.branch = urlParams.branch;
        }
        options[revision.versionIdentifier] = revision.version;

        revision.date = new $osf.FormattableDate(revision.modified);
        revision.displayDate = revision.date.local !== 'Invalid date' ?
            revision.date.local :
            revision.date;

        switch (file.provider) {
            // Note: Google Drive version identifiers often begin with the same sequence
            case 'googledrive':
                revision.displayVersion = revision.version.substring(revision.version.length - 8);
                break;
            // Note: Dataverse internal version names are ugly; Substitute our own
            case 'dataverse':
                var displayMap = {
                    'latest': 'Draft',
                    'latest-published': 'Published'
                };

                revision.displayVersion = revision.version in displayMap ?
                    displayMap[revision.version] : revision.version.substring(0, 8);
                break;
            default:
                revision.displayVersion = revision.version.substring(0, 8);
        }

        if (file.provider === 'osfstorage' && file.name && index !== 0) {
            var parts = file.name.split('.');
            if (parts.length === 1) {
                options.displayName = parts[0] + '-' + revision.modified;
            } else {
                options.displayName = parts.slice(0, parts.length - 1).join('') + '-' + revision.modified + '.' + parts[parts.length - 1];
            }
        }

        revision.osfViewUrl = '?' + $.param(options);
        revision.osfDownloadUrl = '?' + $.param($.extend({action: 'download'}, options));
        revision.waterbutlerDownloadUrl = waterbutler.buildDownloadUrl(file.path, file.provider, node.id, options);

        return revision;
    }
};

module.exports = FileRevisionsTable;
