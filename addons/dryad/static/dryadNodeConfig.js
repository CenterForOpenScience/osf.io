'use strict';

var ko = require('knockout');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers');
var m = require('mithril');
var waterbutler = require('js/waterbutler');
var language = require('js/osfLanguage.js');
var oop = require('js/oop');

var OauthAddonFolderPicker = require('js/oauthAddonNodeConfig')._OauthAddonNodeConfigViewModel;

var $importModal = $('#dryadImportModal');

var DryadFolderPickerViewModel = oop.extend(OauthAddonFolderPicker, {
    constructor: function(url, selector) {
        var self = this;
        self.super.constructor('dryad', url, selector);

        // Fields specific to the current addon status
        self.doi = ko.observable("");
        self.title = ko.observable("");
        self.ident = ko.observable("");
        self.authors = ko.observable("");
        self.dateSubmitted = ko.observable("");
        self.dateAvailable = ko.observable("");
        self.description = ko.observable("");
        self.subjects = ko.observable("");
        self.scientificNames = ko.observable("");
        self.temporalInfo = ko.observable("");
        self.references = ko.observable("");
        self.files = ko.observable("");

        // Browser fields
        self.inSearchMode = false;
        self.totalResults = ko.observable(0);
        self.firstIndex = ko.observable(0);
        self.lastIndex = ko.observable(0);
        self.packages = ko.observableArray();
        self.searchTerms = ko.observable("");

        // Citation fields
        self.packageCitation = ko.observable("");
        self.publicationCitation = ko.observable("");

        self.messages.validateSuccess = ko.pureComputed(function() {
            return 'DOI Successfully Validated: ' + self.doi();
        });
        self.messages.validateFailure = ko.pureComputed(function() {
            return 'Could Not Validate DOI: ' + self.doi();
        });
        self.messages.setDOISuccess = ko.pureComputed(function() {
            return "DOI Successfully set: " + self.doi();
        });
        self.messages.setDOIFailure = ko.pureComputed(function() {
            return "Failed to Set DOI: " + self.doi();
        });
        self.messages.searchError = ko.pureComputed(function() {
            return "Error Searching Terms: " + self.searchTerms();
        });
    },
    osf_safe_doi: function() {
        /*
            Returns an OSF safe DOI
        */
        var self = this;
        return self.doi().split("doi:").pop();
    },
    fetch: function() {
        /*
            Fetches node settings.
        */
        var self = this;
        $.getJSON(self.url).done(function(response) {
            self.node_id = response.result.node_id;
            self.urls(response.result.urls);
            self.doi(response.result.doi);
        }).fail(function(xhr, textStatus, error) {
            self.changeMessage(language.projectSettings.updateErrorMessage,
                'text-danger');
            Raven.captureMessage(language.projectSettings.updateErrorMessage, {
                extra: {
                    url: self.url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    },
    browseTo: function(count, startN) {
        /*
            Sets the browser fields to `count` entries starting at `startN`
        */
        var self = this;
        $('#browser_loading').show();
        $('#browser_wrapper').hide();
        $.get(self.urls().dryad_list_objects, {
                'count': count,
                'start': startN
            })
            .done(function(response) {
                self.firstIndex(response.start);
                self.totalResults(response.total);
                self.lastIndex(response.end);
                ko.utils.arrayForEach(response.package_list,
                    function(d_pack) {
                        d_pack["isVisible"] = ko.observable(false);
                        d_pack['parent'] = self;
                    });
                self.packages(response.package_list);
                $('#browser_loading').hide();
                $('#browser_wrapper').show();
            })
            .fail(function(xhr, status, error) {
                $('#browser_loading').hide();
                $('#browser_wrapper').show();
                self.changeMessage(self.messages.browseError(), 'text-warning');

                Raven.captureMessage(self.messages.browseError(), {
                    extra: {
                        url: self.urls().dryad_list_objects,
                        textStatus: status,
                        error: error
                    }
                });
            });
    },
    searchTo: function(query, count, startN) {
        /*
            Searches the Dryad archive for `query` for `count` entries
            starting at `startN`
        */
        var self = this;
        self.inSearchMode = true;
        $('#browser_loading').show();
        $('#browser_wrapper').hide();
        $.get(self.urls().dryad_search_objects, {
                'query': self.searchTerms(),
                'count': count,
                'start': startN
            })
            .done(function(response) {
                self.firstIndex(response.start);
                self.totalResults(response.total);
                self.lastIndex(response.start + count);
                ko.utils.arrayForEach(response.package_list,
                    function(d_pack) {
                        d_pack["isVisible"] = ko.observable(false);
                        d_pack['parent'] = self;
                    }
                );
                self.packages(response.package_list);
                $('#browser_loading').hide();
                $('#browser_wrapper').show();
            })
            .fail(function(xhr, status, error) {
                self.changeMessage(self.messages.searchError(), 'text-danger');
                Raven.captureMessage(self.messages.searchError(), {
                    extra: {
                        url: self.urls().dryad_search_objects,
                        textStatus: status,
                        error: error
                    }
                });
            });
    },
    getNext: function() {
        var self = this;
        var count = self.lastIndex() - self.firstIndex();
        var startN = self.lastIndex() + 1;
        if (self.inSearchMode) {
            self.searchTo(self.searchTerms(), count, startN);
        } else {
            self.browseTo(count, startN);
        }
    },
    getPrevious: function() {
        var self = this;
        var count = self.lastIndex() - self.firstIndex();
        var startN = self.firstIndex() - count - 1;
        if (self.inSearchMode) {
            self.searchTo(self.searchTerms(), count, startN);
        } else {
            self.browseTo(count, startN);
        }
    },
    search: function() {
        var self = this;
        self.searchTo(self.searchTerms(), 20, 0);
    },
    validateDOI: function() {
        var ret = $.Deferred();
        var self = this;
        $.getJSON(self.urls().dryad_validate_doi, {
            'doi': self.osf_safe_doi()
        }).done(function(result) {
            if (result) {
                self.changeMessage(self.messages.validateSuccess(),
                    'text-success');
                ret.resolve(self.messages.validateSuccess());
            } else {
                self.changeMessage(self.messages.validateFailure(),
                    'text-danger');
                Raven.captureMessage(self.messages.validateFailure(), {
                    url: self.urls().dryad_validate_doi,
                    extra: {
                        doi: self.osf_safe_doi()
                    }
                });
                ret.reject(self.messages.validateFailure());
            }
        }).fail(function(xhr, textStatus, error) {
            self.changeMessage(language.projectSettings.updateErrorMessage,
                'text-danger');
            Raven.captureMessage(language.projectSettings.updateErrorMessage, {
                extra: {
                    url: self.urls().dryad_validate_doi,
                    textStatus: textStatus,
                    error: error
                }
            });
            ret.reject(language.projectSettings.updateErrorMessage);
        });
        return ret;
    },
    setDOIBrowser: function() {
        var self = this;
        self.parent.doi(self.doi);
        self.parent.setDOI();
    },
    setDOI: function() {
        var self = this;
        var ret = $.Deferred();
        $importModal.modal('show');
        self.validateDOI().done(function() {
            $osf.putJSON(self.urls().dryad_set_doi, {
                    'doi': self.osf_safe_doi()
                })
                .then(function() {
                    self.changeMessage(self.messages.setDOISuccess(), 'text-success');
                    self.refreshMetadata().then(function() {
                        self.createPackageFolder();
                        ret.resolve(self.messages.setDOISuccess());
                    });
                }, function(data) {
                    self.changeMessage(self.messages.setDOIFailure(), 'text-danger');
                    Raven.captureMessage(self.messages.setDOIFailure(), {
                        extra: {
                            url: self.urls().dryad_set_doi,
                            textStatus: data.responseText,
                            error: data.status,
                            data: self.osf_safe_doi()
                        }
                    });
                    ret.reject(language.projectSettings.updateErrorMessage);
                });
        });
        return ret;
    },
    refreshMetadata: function() {
        var self = this;
        $('#dryad-node-spinner-loading').show();
        $('#dryad-node-details').hide();
        var ret = $.Deferred();
        $.get(self.urls().dryad_get_current_metadata, {
                doi: self.osf_safe_doi()
            })
            .done(function(response) {
                self.doi(response.doi);
                self.title(response.title);
                self.ident(response.ident);
                self.authors(response.authors);
                self.dateSubmitted(response.date_submitted);
                self.dateAvailable(response.date_available);
                self.description(response.description);
                self.subjects(response.subjects);
                self.scientificNames(response.scientificNames);
                self.temporalInfo(response.temporalInfo);
                self.references(response.references);
                self.files(response.files);
                $('#dryad-node-spinner-loading').hide();
                $('#dryad-node-details').show();
                ret.resolve();
            })
            .fail(function(xhr, status, error) {
                self.changeMessage(language.projectSettings.updateErrorMessage,
                    'text-danger');
                $('#dryad-node-spinner-loading').hide();
                $('#dryad-node-details').show();
                Raven.captureMessage(language.projectSettings.updateErrorMessage, {
                    extra: {
                        url: self.urls().dryad_validate_doi,
                        textStatus: status,
                        error: error
                    }
                });
                ret.reject(language.projectSettings.updateErrorMessage);
            });
        return ret;
    },
    makeLicensingInformation: function(path) {
        /*
            Creates the licensing information that will be transferred to osfstorage

            Note that currently, buildTreeBeardUpload is being used since buildUrl
            is broken (needs type:files-> type:file).
        */
        var self = this;
        var xhr = new XMLHttpRequest();
        xhr.open("PUT", waterbutler.buildMetadataUrl(path, 'osfstorage', self.node_id, {
            name: 'DRYAD_LICENSE.md',
            kind: 'file'
        }), true);
        xhr.setRequestHeader("Content-type", "multipart/form-data;");
        $osf.setXHRAuthorization(xhr, null);

        xhr.onreadystatechange = function() {
            if (xhr.readyState == 4 && xhr.status == 201) {
                self.changeMessage("Licensing Information Uploaded");
            } else if (xhr.readyState == 4) {
                self.changeMessage("Licensing Information Failed to Upload");
                Raven.captureMessage("Licensing Information Failed to Upload", {
                    extra: {
                        url: waterbutler.buildMetadataUrl(path, 'osfstorage', self.node_id, {
                            name: 'DRYAD_LICENSE.md'
                        }),
                        textStatus: xhr.status,
                        error: xhr.error
                    }
                });
            }
        }
        var body = "Dryad Data is available under a [CC-BY 3.0 license](http://creativecommons.org/licenses/by/3.0/)\n";
        $.getJSON(self.urls().dryad_citation, {'doi': self.osf_safe_doi()}).done(function(response) {
            body += "\n__Please Cite the following paper located at the following URL:__\n\n";
            body += '[' + response.publication + '](' + response.publication + ')\n\n';
            body += "\n__Additionally, Please Cite the following Dryad Package:__\n\n";
            body += response.package + '\n\n';
            body += "\n__Package Metadata:__\n\n```\n";
            body += JSON.stringify({
                doi: self.doi(),
                title: self.title(),
                ident: self.ident(),
                authors: self.authors(),
                date_submitted: self.dateSubmitted(),
                date_available: self.dateAvailable(),
                description: self.description(),
                subjects: self.subjects(),
                scientific_names: self.scientificNames(),
                temporal_info: self.temporalInfo(),
                references: self.references(),
                files: self.files()
            }, null, 2);
            body += '\n```\n';
            xhr.send(body);
        }).fail(function(xhr, textStatus, error) {
            self.changeMessage(language.projectSettings.updateErrorMessage, 'text-danger');
            Raven.captureMessage(language.projectSettings.updateErrorMessage, {
                extra: {
                    url: self.urls().dryad_citation,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    },
    makePackageInformation: function(path) {
        /*
            Creates the package information that will be transferred to osfstorage

            Note that currently, buildTreeBeardUpload is being used since buildUrl
            is broken (needs type:files-> type:file).
        */
        var self = this;
        var xhr = new XMLHttpRequest();
        xhr.open("PUT", waterbutler.buildMetadataUrl(path, 'osfstorage', self.node_id, {
            name: 'DRYAD_PACKAGE.md',
            kind: 'file'
        }), true);
        xhr.setRequestHeader("Content-type", "multipart/form-data;");
        $osf.setXHRAuthorization(xhr, null);

        xhr.onreadystatechange = function() {
            if (xhr.readyState == 4 && xhr.status == 201) {
                self.changeMessage("Package Information Uploaded");
                self.uploadFiles(self.osf_safe_doi(), path);
            } else if (xhr.readyState == 4) {
                self.changeMessage("Package Information Failed to Upload");
                Raven.captureMessage("Package Information Failed to Upload", {
                    extra: {
                        url: waterbutler.buildMetadataUrl(path, 'osfstorage', self.node_id, {
                            name: 'DRYAD_PACKAGE.md'
                        }),
                        textStatus: xhr.status,
                        error: xhr.error
                    }
                });
            }
        }
        var body = "__" + self.title() + "__\n\n" + self.description() + "\n\n";
        body += "DOI: [" + self.doi() + "](" + self.ident() + ")\n\n";
        body += "Authors: \n\n"
        for (var i = 0; i < self.authors().length; i++) {
            body += "- " + self.authors()[i] + "\n";
        }
        body += "\nDate Submitted: " + self.dateSubmitted() + "\n\n";
        body += "Date Available: " + self.dateAvailable() + "\n\n";
        if (self.subjects() !== undefined) {
            body += "Subjects: " + self.subjects() + "\n\n";
        }
        if (self.scientificNames() !== undefined) {
            body += "Scientific Names: " + self.scientificNames() + "\n\n";
        }
        if (self.temporalInfo() !== undefined) {
            body += "Temporal Info: " + self.temporalInfo() + "\n\n";
        }
        if (self.references() !== undefined) {
            body += "References: [" + self.references() + "](" + self.references() + ")\n\n";
        }
        if (self.files() !== undefined) {
            body += "Files: [" + self.files() + "](" + self.files() + ")\n\n";
        }
        xhr.send(body);
    },
    uploadSingleFile: function(doi, dest_path, files, index) {
        /*
            Initiates a copy of a single file from dryad to osfstorage, then
            calls the next copy in the sequence. This way, if the user refreshes
            the page immediately after the transfer begins, the sequence won't
            be interrupted.

        */
        var self = this;
        if (index == files.length) {
            self.changeMessage("Done!", 'text-success');
            $importModal.modal("hide");
            return;
        }
        var doi_split = files[index].id;
        var sub_doi = doi_split.replace('dryad','');
        var payload = {
            action:'copy',
            path: dest_path,
            conflict: 'replace',
            resource: self.node_id,
            provider: 'osfstorage'
        };
        $.ajax({
            type: 'POST',
            beforeSend: $osf.setXHRAuthorization,
            url: waterbutler.buildUploadUrl( sub_doi, 'dryad', self.node_id, {}),
            headers: {
                'Content-Type': 'Application/json'
            },
            data: JSON.stringify(payload)
        }).then(function() {
            self.changeMessage("File Transferred", 'text-success');
        }, function(data) {
            self.changeMessage(language.Addons.dryad.doiExistsFailure, 'text-danger');
            Raven.captureMessage(language.Addons.dryad.doiExistsFailure, {
                extra: {
                    url: waterbutler.buildUploadUrl(sub_doi, 'dryad', self.node_id, {}),
                    textStatus: data.responseText,
                    error: data.status
                }
            });
            $importModal.modal("hide");
        });
        self.uploadSingleFile(doi, dest_path, files, index + 1);
    },
    uploadFiles: function(doi, dest_path) {
        /*
            Queries WB for file information corresponding to the package pointed
            at by doi, then calls the first single file upload.

            , {
                branch: $osf.urlParams().branch
            }
        */
        var self = this;
        var doi_split = self.doi().split('.');
        var file_id = doi_split.pop();
        m.request({
            background: true,
            config: $osf.setXHRAuthorization,
            url: waterbutler.buildMetadataUrl("/" + file_id + "/", 'dryad', self.node_id)
        }).then(function(item) {
            self.uploadSingleFile(doi, dest_path, item.data, 0);
        }, function(data) {
            self.changeMessage(language.Addons.dryad.doiExistsFailure, 'text-danger');
            Raven.captureMessage(language.Addons.dryad.doiExistsFailure, {
                extra: {
                    url: waterbutler.buildMetadataUrl("/" + file_id + "/", 'dryad',
                        self.node_id, {
                            branch: $osf.urlParams().branch
                        }),
                    textStatus: data.responseText,
                    error: data.status
                }
            });
            $importModal.modal("hide");
        });
    },
    createPackageFolder: function() {
        /*
            Using the metadata in the plugin, creates a folder in osfstorage for the data
            to be dumped in.

            The path is set to '/' by default so that the project data and licensing
            information are always uploaded to a folder sitting in the root directory.
        */
        var self = this;
        var path = '/';//$.trim('/' + self.title());
        var ret = $.Deferred();
        var options = {name: self.title(), kind: 'folder'};

        m.request({
            method: 'PUT',
            background: true,
            config: $osf.setXHRAuthorization,
            url: waterbutler.buildCreateFolderUrl(path, 'osfstorage', self.node_id, options)
        }).then(function(item) {
            var dest_path = item.data.attributes.path;
            self.makeLicensingInformation(dest_path);
            self.makePackageInformation(dest_path);
            ret.resolve(self.messages.setDOISuccess());
        }, function(data) {
            self.changeMessage(language.Addons.dryad.doiExistsFailure, 'text-danger');
            Raven.captureMessage(language.Addons.dryad.doiExistsFailure, {
                extra: {
                    url: waterbutler.buildCreateFolderUrl(path, 'osfstorage', self.node_id, options),
                    textStatus: data.responseText,
                    error: data.status,
                    data: data
                }
            });
            $importModal.modal("hide");
            ret.reject(language.Addons.dryad.doiExistsFailure);
        });
        return ret;
    },
});

var DryadNodeConfig = function(selector, url, folderPicker, opts, tbOpts) {
    var self = this;
    self.selector = selector;
    self.url = url;
    self.folderPicker = folderPicker;
    opts = opts || {};
    tbOpts = tbOpts || {};
    self.viewModel = new DryadFolderPickerViewModel(self.url, self.selector, self.folderPicker, opts, tbOpts);
    $osf.applyBindings(self.viewModel, self.selector);
};

module.exports = {
    DryadNodeConfig: DryadNodeConfig,
    _DryadNodeConfigViewModel: DryadFolderPickerViewModel
};
