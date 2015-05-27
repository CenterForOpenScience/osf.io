var m = require('mithril');
var $ = require('jquery');
var $osf = require('js/osfHelpers');

var util = require('./util.js');


var FileRevisionsTable = {
    controller: function(file) {
        var self = this;
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
                self.loaded = true;
                self.revisions = response.data.map(function(revision) {
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

                    return revision;
                });
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
    }
};

module.exports = FileRevisionsTable;
