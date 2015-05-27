var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');
var waterbutler = require('js/waterbutler');

var util = require('./util.js');


var FileRevisionsTable = {
    controller: function(file, node) {
        var self = this;
        self.node = node;
        self.file = file;
        self.loaded = false;
        self.revisions = [];

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
                m.endComputation();
            }).fail(function(response) {
                //TODO
            });
        };

        self.reload();
    },
    view: function(ctrl) {
        if (!ctrl.loaded) return util.Spinner;
        return m('table.table', [
            m('thead.file-version-thread', [
                m('tr', [
                    m('th', 'Version ID'),
                    m('th', 'Date'),
                    m('th', 'User'),
                    m('th', 'Download'),
                ])
            ]),
            m('tbody.file-version', ctrl.revisions.map(function(revision, index) {
                return m('tr' + (index === ctrl.currentRevision ? '.active' : ''), [
                    m('td', revision.displayVersion),
                    m('td', revision.displayDate),
                    m('td', revision.extra.user),
                    m('td', revision.extra.downloads),
                ]);
            }))
        ]);
    },
    postProcessRevision: function(file, node, revision, index) {
        var options = {};
        var urlParams = $osf.urlParams();

        if (urlParams.branch !== undefined) {
            options.branch = urlParams.branch;
        }
        options[self.versionIdentifier] = self.version;

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

        // if (file.provider === 'osfstorage' && file.name && index !== 0) {
        //     var parts = file.name.split('.');
        //     if (parts.length === 1) {
        //         options.displayName = parts[0] + '-' + data.modified;
        //     } else {
        //         options.displayName = parts.slice(0, parts.length - 1).join('') + '-' + data.modified + '.' + parts[parts.length - 1];
        //     }
        // }

        self.osfViewUrl = '?' + $.param(options);
        self.osfDownloadUrl = '?' + $.param($.extend({action: 'download'}, options));
        self.waterbutlerDownloadUrl = waterbutler.buildDownloadUrl(file.path, file.provider, node.id, options);

        self.download = function() {
            window.location = self.waterbutlerDownloadUrl;
            return false;
        };

        return revision;
    }
};

module.exports = FileRevisionsTable;
