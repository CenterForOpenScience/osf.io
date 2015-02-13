var m = require('mithril');
var $osf = require('osfHelpers');
var waterbutler = require('waterbutler');
var FileRenderer = require('../filerenderer.js');
var FileRevisions = require('../fileRevisions.js');

if (window.contextVars.renderURL !== undefined) {
    FileRenderer.start(window.contextVars.renderURL, '#fileRendered');
}

new FileRevisions(
    '#fileRevisions',
    window.contextVars.node,
    window.contextVars.file,
    window.contextVars.currentUser.canEdit
);

// TODO: Workaround for highlighting the Files tab in the project navbar. Rethink.
$(document).ready(function(){
    $('.osf-project-navbar li:contains("Files")').addClass('active');
});

var RevisionsBar = {};

RevisionsBar.controller = function(pagevm) {
    var self = this;
    self.vm = pagevm;

    self.renderRevision = function(rev) {
        return m(self.vm.revision === rev ? 'tr.info' : 'tr', [
            m('td', m('a', {href: rev.viewUrl}, rev.shortVersion)),
            m('td', rev.displayDate),
            m('td', rev.extra.downloads > -1 ? m('.badge', rev.extra.downloads) : ''),
            m('td', [
                m('a.btn.btn-primary.btn-sm',
                  {href: rev.downloadUrl},
                  m('i.icon-download-alt'))
            ]),
        ]);
    };
};

RevisionsBar.view = function(ctrl) {
    if (!ctrl.vm.revisionsLoaded) {
        return m('img[src=/static/img/loading.gif]');
    }

    if (ctrl.vm.revisionsLoadedFailed) {
        return m('.alert.alert-warning', ctrl.vm.revisionErrorMessage);
    }

    return m('table.table', [
        m('thead', [
            m('tr',[
                m('th', 'Version'),
                m('th', 'Date'),
                m('th[colspan=2]', 'Download')
            ])
        ]),
        m('tbody', ctrl.vm.revisions.map(ctrl.renderRevision))
    ]);
};


var FileRenderBlock = {};

FileRenderBlock.view = function(ctrl) {
    if (!ctrl.renderComplete) {
        return m('img[src=/static/img/loading.gif]');
    }
    if (ctrl.renderFailed) {
        return ctrl.renderFailureMessage;
    }
    return m('.mfr.mfr-file', m.trust(ctrl.rawHtml));
};

FileRenderBlock.controller = function(pagevm) {
    var self = this;
    self.vm = pagevm;
    self.attempts = 0;
    self.allowedAttempts = 5;
    self.renderFailured = false;
    self.renderComplete = false;
    self.renderFailureMessage = m('span', 'The was an issue when attempting to render this file.');

    self.render = function(result) {
        self.renderComplete = true;
        self.rawHtml = result;
    };

    self.retry = function(data) {
        self.attempts++;
        if (self.attempts > self.allowedAttempts) {
            self.renderFailured = true;

        } else {
            m.request({
                method: 'GET',
                url: self.vm.file.urls.render
            }).then(self.render, self.retry);
        }
    };

    m.request({
        method: 'GET',
        url: self.vm.urls.render
    }).then(self.render, self.retry);
};


var FileActionBlock = {};

FileActionBlock.view = function(ctrl) {
    return m('.btn-toolbar', [
        m('ol.breadcrumb', ctrl.breadcrumbs()),
        m('a.btn.btn-success.btn-md', {href: ctrl.downloadUrl()}, [
            'Download ', m('i.icon-download-alt')
        ]),
        m('button.btn.btn-danger.btn-md', ['Delete ', m('i.icon-trash')])
    ]);
};

FileActionBlock.controller = function(pagevm) {
    var self = this;
    self.vm = pagevm;
    self.pathSegments = [self.vm.file.provider].concat(self.vm.file.path.split('/').slice(1));

    self.download = function() {
        document.location = self.vm.revision.waterbutlerDownloadUrl || self.vm.file.urls.download;
        return false;
    };

    self.downloadUrl = function() {
        return self.vm.revision ? self.vm.revision.downloadUrl : '?action=download';
    };

    self.delete = function() {
    };

    self.breadcrumbs = function() {
        return [
            m('li', m('a', {href: self.vm.node.urls.files}, self.vm.node.title))
        ].concat(self.pathSegments.map(function(segment) {
            return m('li.active.overflow', segment);
        }));
    };
};


var FileViewPage = {};

FileViewPage.File = function(data) {
    var self = this;

    $.extend(self, data);
};

FileViewPage.Revision = function(index, data, file, node) {
    var ops = {};
    var self = this;

    $.extend(self, data);

    ops[self.versionIdentifier] = self.version;
    self.shortVersion = self.version.substring(0, 8);

    self.date = new $osf.FormattableDate(data.modified);
    self.displayDate = self.date.local !== 'Invalid date' ?
        self.date.local :
        data.date;

    // Append modification time to file name if OSF Storage and not current version
    if (file.provider === 'osfstorage' && file.name && index !== 0) {
        var parts = file.name.split('.');
        if (parts.length === 1) {
            ops.displayName = parts[0] + '-' + data.modified;
        } else {
            ops.displayName = parts.slice(0, parts.length - 1).join('') + '-' + data.modified + '.' + parts[parts.length - 1];
        }
    }

    self.viewUrl = '?' + $.param(ops);
    self.downloadUrl = '?' + $.param($.extend({action: 'download'}, ops));
    self.waterbutlerDownloadUrl = waterbutler.buildDownloadUrl(file.path, file.provider, node.id, ops);
};

FileViewPage.ViewModel = function() {
    var self = this;

    self.fileLoaded = false;
    self.revisionsLoaded = false;

    self.fileLoadedFailed = false;
    self.revisionsLoadedFailed = false;

    self.revisionErrorMessage = 'Unable to fetch versions.';
    self.fileErrorMessage = 'Unable to retrieve file information.';

    self.fileCanBeDeleted = true;
    self.fileCanBeDownloaded = true;

    self.node = window.contextVars.node;
    self.filePath = window.contextVars.file.path;
    self.provider = window.contextVars.file.provider;
    self.urls = {
        render: window.contextVars.renderUrl,
        metadata: waterbutler.buildMetadataUrl(self.filePath, self.provider, self.node.id),
        revisions: waterbutler.buildRevisionsUrl(self.filePath, self.provider, self.node.id),
    };

    self.loadFile = function(data) {
        self.fileLoaded = true;

        self.file = new FileViewPage.File(data.data);

        self.fileRenderBlockCtrl = new FileRenderBlock.controller(self);
        self.fileActionBlockCtrl = new FileActionBlock.controller(self);
    };

    self.loadRevisions = function(data) {
        self.revisionsLoaded = true;

        self.revision = undefined;

        self.revisions = data.data.map(function(item, index) {
            if ($osf.urlParams()[item.versionIdentifier] === item.version) {
                self.revision = new FileViewPage.Revision(index, item, self.file, self.node);
                return self.revision;
            }

            return new FileViewPage.Revision(index, item, self.file, self.node);
        });

        self.revision = self.revision || self.revisions[0];

        self.revisionsBarCtrl = new RevisionsBar.controller(self);
    };

    self.loadFileFail = function(data) {
        self.fileLoadedFailed = true;
    };

    self.loadRevisionsFail = function(data) {
        self.revisionsLoadedFailed = true;
    };

    self.init = function() {
        m.request({
            method: 'GET',
            url: self.urls.metadata
        }).then(self.loadFile, self.loadFileFail).then(function() {
            m.request({
                method: 'GET',
                url: self.urls.revisions
            }).then(self.loadRevisions, self.loadRevisionsFail);
        }
    );

    };
};

FileViewPage.controller = function() {
    var self = this;
    self.vm = new FileViewPage.ViewModel();
    self.vm.init();
};

FileViewPage.view = function(ctrl) {
    if (!ctrl.vm.fileLoaded) {
        return m('img[src=/static/img/loading.gif]');
    }

    return [
        m('h2', ctrl.vm.file.name),
        m('hr'),
        m('.row', [
            m('.col-md-8', FileRenderBlock.view(ctrl.vm.fileRenderBlockCtrl)),
            m('.col-md-4', [
                FileActionBlock.view(ctrl.vm.fileActionBlockCtrl),
                RevisionsBar.view(ctrl.vm.revisionsBarCtrl)
            ])
        ])
    ];
};

m.module(document.getElementById('mithril'), FileViewPage);
