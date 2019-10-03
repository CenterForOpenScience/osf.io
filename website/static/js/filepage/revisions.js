var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

var util = require('./util.js');
var makeClient = require('js/clipboard');

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
    hasHashes: false,
    selectedRevision: 0
};


var FileRevisionsTable = {
    controller: function(file, node, enableEditing, canEdit, selectLatest) {
        var self = {};
        self.node = node;
        self.file = file;
        self.canEdit = canEdit;
        self.enableEditing = enableEditing;
        self.baseUrl = (window.location.href).split('?')[0];
        self.selectLatest = selectLatest;

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
                response = waterbutler.wbLazyLoadPreprocess.call(this, response);
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
                    self.selectLatest();
                }
                model.hasUser = model.revisions[0] && model.revisions[0].extra && model.revisions[0].extra.user;
                model.hasHashes = model.revisions && model.revisions[0] && model.revisions[0].extra.hashes;
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
                        resp = waterbutler.wbLazyLoadPreprocess.call(this, resp);
                        self.canEdit(self.canEdit() && resp.data.extra.canDelete);
                        m.redraw();
                    }).fail(function(xhr) {
                        self.canEdit(false);
                        m.redraw();
                    });
                }
            });
        };


        var popOver = function(element, isInit) {
            if (!isInit) {
                $(element).popover();
            }
        };

        self.getTableHead = function() {
            return m('thead', [
                m('tr', [
                    m('th', 'Version ID'),
                    model.hasDate ? m('th', 'Date') : false,
                    model.hasUser ? m('th', 'User') : false,
                    m('th[colspan=2]', 'Download'),
                    model.hasHashes ? m('th', [
                        'MD5 ', m('.fa.fa-question-circle[data-content="MD5 is an algorithm used to verify data integrity."][rel="popover"]' +
                            '[data-placement="top"][data-trigger="hover"]', {config: popOver}) ]) : false,
                    model.hasHashes ? m('th', [
                        'SHA2 ', m('.fa.fa-question-circle[data-content="SHA-2 is a cryptographic hash function designed by the NSA used to verify data integrity."][rel="popover"]' +
                            '[data-placement="top"][data-trigger="hover"]', {config: popOver}) ]) : false,
                ].filter(TRUTHY))
            ]);

        };

        self.makeTableRow = function(revision, index) {
            var isSelected = index === model.selectedRevision;
            var clipBoard = function(element) {
                makeClient(element);
            };
            return m('tr' + (isSelected ? '.active' : ''), [
                m('td',  isSelected ? revision.displayVersion :
                  m('a', {href: parseInt(revision.displayVersion) === model.revisions.length ? self.baseUrl : revision.osfViewUrl}, revision.displayVersion)
                ),
                model.hasDate ? m('td', revision.displayDate) : false,
                model.hasUser ? window.contextVars.node.anonymous ? m('td', 'Anonymous Contributor') :
                    m('td', revision.extra.user.url ?
                            m('a', {href: revision.extra.user.url}, revision.extra.user.name) :
                            revision.extra.user.name
                    ) : false,
                m('td', revision.extra.downloads > -1 ? m('.badge', revision.extra.downloads) : ''),
                m('td',
                    m('a.btn.btn-primary.btn-sm.file-download', {
                        href: revision.osfDownloadUrl,
                        onclick: function() {
                            window.location = revision.osfDownloadUrl;
                            return false;
                        }
                    }, m('i.fa.fa-download'))
                ),
                model.hasHashes ? m('td',
                    m('div.input-group[style="width: 180px"]',
                        [
                            m('span.input-group-btn', m('button.btn.btn-default.btn-sm[type="button"][data-clipboard-text="'+revision.extra.hashes.md5 + '"]', {config: clipBoard}, m('.fa.fa-copy'))),
                            m('input[value="'+revision.extra.hashes.md5+'"][type="text"][readonly="readonly"][style="float:left; height: 30px;"]')
                        ]
                    )) : false,
                model.hasHashes ? m('td',
                    m('div.input-group[style="width: 180px"]',
                        [
                            m('span.input-group-btn', m('button.btn.btn-default.btn-sm[type="button"][data-clipboard-text="'+revision.extra.hashes.sha256 + '"]',{config: clipBoard}, m('.fa.fa-copy'))),
                            m('input[value="'+revision.extra.hashes.sha256+'"][type="text"][readonly="readonly"][style="float:left; height: 30px;"]')
                        ]
                    )) : false
            ].filter(TRUTHY));
        };

        if (!model.loaded()) {
            self.reload();
        }
        $(document).on('fileviewpage:reload', self.reload);
        return self;
    },
    view: function(ctrl) {
        return m('#revisionsPanel.panel.panel-default', [
            m('.panel-heading.clearfix', m('h3.panel-title', 'Revisions')),
            m('.panel-body', {style:{'padding-right': '0','padding-left':'0', 'padding-bottom' : '0',
                'overflow': 'auto'}}, (function() {
                if (!model.loaded()) {
                    return util.Spinner;
                }
                if (model.errorMessage) {
                    return m('.alert.alert-warning', {style:{margin: '10px'}}, model.errorMessage);
                }
                return m('table.table.table-responsive', {style:{marginBottom: '0'}}, [
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

        revision.date = new $osf.FormattableDate(revision.modified_utc);
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
            var parts;
            if (file.versionNames && file.versionNames.length) {
                parts = file.versionNames[index].split('.');
            } else {
                parts = file.name.split('.');
            }
            if (parts.length === 1) {
                options.displayName = parts[0] + '-' + revision.modified;
            } else {
                options.displayName = parts.slice(0, parts.length - 1).join('') + '-' + revision.modified + '.' + parts[parts.length - 1];
            }
        }

        revision.osfViewUrl = '?' + $.param(options);
        revision.osfDownloadUrl = !index ? 'download' : 'download?' + $.param(options);

        return revision;
    }
};

module.exports = FileRevisionsTable;
