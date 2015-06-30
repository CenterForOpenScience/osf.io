var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

var util = require('./util.js');

// Helper for filtering
function TRUTHY(item) {
    return !!item; //Force cast to a bool
}


var model = {
    revisions: [],
    loaded: m.prop(false),
    errorMessage: undefined,
    hasUser: false,
    hasDate: false,
    selectedRevision: 0
};


var FileRevisionsTable = {
    controller: function(file, node, enableEditing, canEdit) {
        var self = {};
        self.node = node;
        self.file = file;
        self.canEdit = canEdit;
        self.enableEditing = enableEditing;
        self.baseUrl = (window.location.href).split('?')[0];

        model.hasDate = self.file.provider !== 'dataverse';

        self.reload = function() {
            model.loaded(false);
            m.redraw();
            $.ajax({
                dataType: 'json',
                async: true,
                url: self.file.urls.revisions,
                beforeSend: $osf.setXHRAuthorization
            }).done(function(response) {
                m.startComputation();
                var urlParmas = $osf.urlParams();
                model.revisions = response.data.map(function(rev, index) {
                    rev = FileRevisionsTable.postProcessRevision(self.file, self.node, rev, index);
                    if (urlParmas[rev.versionIdentifier] === rev.version) {
                        model.selectedRevision = index;
                    }
                    return rev;
                });
                model.loaded(true);
                // Can only edit the latest version of a file
                if (model.selectedRevision === 0) {
                    self.enableEditing();
                }
                model.hasUser = model.revisions[0] && model.revisions[0].extra && model.revisions[0].extra.user;
                m.endComputation();
            }).fail(function(response) {
                m.startComputation();
                model.loaded(true);
                model.errorMessage = response.responseJSON ?
                    response.responseJSON.message || 'Unable to fetch versions' :
                    'Unable to fetch versions';
                m.endComputation();

                // model.errorMessage(err);

                if (self.file.provider === 'figshare') {
                    // Hack for Figshare
                    // only figshare will error on a revisions request
                    // so dont allow downloads and set a fake current version
                    $.ajax({
                        method: 'GET',
                        url: self.file.urls.metadata,
                        beforeSend: $osf.setXHRAuthorization
                    }).done(function(resp) {
                        self.canEdit(self.canEdit() && resp.data.extra.canDelete);
                        m.redraw();
                    }).fail(function(xhr) {
                        self.canEdit(false);
                        m.redraw();
                    });
                }
            });
        };

        self.getTableHead = function() {
            return m('thead', [
                m('tr', [
                    m('th', 'Version ID'),
                    model.hasDate ? m('th', 'Date') : false,
                    model.hasUser ? m('th', 'User') : false,
                    m('th[colspan=2]', 'Download'),
                ].filter(TRUTHY))
            ]);
        };

        self.makeTableRow = function(revision, index) {
            var isSelected = index === model.selectedRevision;

            return m('tr' + (isSelected ? '.active' : ''), [
                m('td',  isSelected ?
                  revision.displayVersion :
                  m('a', {href: parseInt(revision.displayVersion) === model.revisions.length ? self.baseUrl : revision.osfViewUrl}, revision.displayVersion)
                ),
                model.hasDate ? m('td', revision.displayDate) : false,
                model.hasUser ?
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

        if (!model.loaded()) {
            self.reload();
        }
        $(document).on('fileviewpage:reload', self.reload);
        return self;
    },
    view: function(ctrl) {
        return m('#revisionsPanel', [
            m('.osf-panel-header', 'Revisions'),
            m('', (function() {
                if (!model.loaded()) {
                    return util.Spinner;
                }
                if (model.errorMessage) {
                    return m('.alert.alert-warning', {style:{margin: '10px'}}, model.errorMessage);
                }

                return m('table.table', [
                    ctrl.getTableHead(),
                    m('tbody', model.revisions.map(ctrl.makeTableRow))
                ]);
            })())
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
