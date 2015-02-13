var m = require('mithril');
var $osf = require('osfHelpers');
var bootbox = require('bootbox');
var waterbutler = require('waterbutler');

var jsonOrXhr = function(xhr) {
    //https://lhorie.github.io/mithril/mithril.request.html#using-variable-data-formats
    return xhr.status === 200 ? xhr.responseText : xhr;
};

var deserialize = function(xhrorjson) {
    if (typeof xhrorjson.onreadystatechange === 'function') {
        return xhrorjson;
    }
    return JSON.parse(xhrorjson);
};

var ExceptionsToErrorMessage = {
    404: m('.alert.alert-info[role=alert]',
           'The requested file either does not exist or no longer exists.'),
    410: m('.alert.alert-info[role=alert]',
           'The requested file has been deleted.')
};

//https://github.com/janl/mustache.js/blob/master/mustache.js#L43
var entityMap = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    '\'': '&#39;',
    '/': '&#x2F;'
};

function escapeHtml(string) {
    return String(string).replace(/[&<>"'\/]/g, function (s) {
        return entityMap[s];
    });
}

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
    self.renderFailed = false;
    self.renderComplete = false;
    self.renderFailureMessage = m('span', 'The was an issue when attempting to render this file.');

    self.render = function(result) {
        if (result === null) {
            self.throttledRetry();
        } else{
            self.rawHtml = result;
            self.renderComplete = true;
        }
    };

    self.retry = function(data) {
        self.attempts++;
        if (self.attempts > self.allowedAttempts) {
            self.renderFailed = true;
            self.renderComplete = true;

        } else {
            m.request({
                method: 'GET',
                extract: jsonOrXhr,
                deserialize: deserialize,
                url: self.vm.urls.render
            }).then(self.render, self.throttledRetry);
        }
    };

    self.throttledRetry = $osf.throttle(self.retry, 10000);

    m.request({
        method: 'GET',
        extract: jsonOrXhr,
        deserialize: deserialize,
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
        m('button.btn.btn-danger.btn-md', {onclick: ctrl.delete}, ['Delete ', m('i.icon-trash')])
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

    self.realDelete = function() {
        m.request({
            method: 'DELETE',
            url: self.vm.urls.delete,
        }).then(function() {
            window.location = self.vm.node.urls.files;
        }, function() {
            $osf.growl('Error', 'Could not delete file.');
        });
    };

    self.delete = function() {
        bootbox.confirm({
            title: 'Delete file?',
            message: '<p class="overflow">' +
                    'Are you sure you want to delete <strong>' +
                    escapeHtml(self.vm.file.name) + '</strong>?' +
                '</p>',
            callback: function(confirm) {
                if (confirm) {
                    self.realDelete();
                }
            }
        });
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

    self.revisionErrorMessage = m('Unable to fetch versions.');
    self.fileErrorMessage = m('.alert.alert-info[role=alert]', [
        'This file is currently unable to be rendered.', m('br'),
        'If this should not have occurred and the issue persists, ',
        'please report it to ', m('a[href=mailto:support@osf.io]', 'support@osf.io')
    ]);

    self.fileCanBeDeleted = true;
    self.fileCanBeDownloaded = true;

    self.node = window.contextVars.node;
    self.filePath = window.contextVars.file.path;
    self.provider = window.contextVars.file.provider;
    self.urls = {
        render: window.contextVars.renderUrl,
        delete: waterbutler.buildDeleteUrl(self.filePath, self.provider, self.node.id),
        metadata: waterbutler.buildMetadataUrl(self.filePath, self.provider, self.node.id),
        revisions: waterbutler.buildRevisionsUrl(self.filePath, self.provider, self.node.id),
    };

    self.loadFile = function(data) {
        self.fileLoaded = true;

        self.file = new FileViewPage.File(data.data);

        document.title = 'OSF | ' + self.file.name;

        m.request({
            method: 'GET',
            extract: jsonOrXhr,
            deserialize: deserialize,
            url: self.urls.revisions,
        }).then(self.loadRevisions, self.loadRevisionsFail);

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

    self.loadFileFail = function(xhr) {
        self.fileLoaded = true;
        self.fileLoadedFailed = true;
        self.fileErrorMessage = ExceptionsToErrorMessage[xhr.status] || self.fileErrorMessage;
    };

    self.loadRevisionsFail = function(data) {
        self.revisionsLoaded = true;
        self.revisionsLoadedFailed = true;
    };

    self.init = function() {
        m.request({
            method: 'GET',
            extract: jsonOrXhr,
            url: self.urls.metadata,
            deserialize: deserialize,
        }).then(self.loadFile, self.loadFileFail);
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

    if (ctrl.vm.fileLoadedFailed) {
        return ctrl.vm.fileErrorMessage;
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

module.exports = FileViewPage;
