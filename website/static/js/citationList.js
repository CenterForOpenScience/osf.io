'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('./osfHelpers');
var citations = require('./citations');
var bootbox = require('bootbox');

var BASE_URL = '/static/vendor/bower_components/styles/';
var STYLES = {
    apa: 'apa.csl',
    mla: 'modern-language-association.csl',
    chicago: 'chicago-author-date.csl'
};

var ctx = window.contextVars;

var formatCitation = function(style, data, format) {
    var citeproc = citations.makeCiteproc(style, data, format);
    return citeproc.makeBibliography()[1];
};

var ViewModel = function(citations, user) {

    var self = this;

    self.user = ko.observable(user);
    self.userIsAdmin  = $.inArray('admin', user.permissions) !== -1;

    self.citations = ko.observableArray([]);

    self.citations(citations.map(function(item) {
            return new AlternativeModel(item, 'view');
        }));

    self.editing = ko.observable(false);

    self.addAlternative = function() {
        self.citations.push(new AlternativeModel());
        self.editing(true);
    };
    self.apa = ko.observable();
    self.mla = ko.observable();
    self.chicago = ko.observable();
};

var AlternativeModel = function(citation, view) {
    var self = this;

    self.init = function() {
        if (citation !== undefined) {
            $.extend(self, citation);
            self.name = ko.observable(citation.name);
            self.text = ko.observable(citation.text);
            self.id = citation.id;
            self.view = ko.observable(view);
            self.originalValues = {
                name: citation.name,
                text: citation.text
            };
        }
        else {
            self.name = ko.observable();
            self.text = ko.observable();
            self.view = ko.observable();
            self.edit();
        }

        self.messages = ko.observableArray([]);
    };

    self.removeSelf = function(parent) {
        if (self.originalValues !== undefined) {
            bootbox.confirm({
                title: 'Delete citation?',
                message: ('Are you sure you want to remove this citation (<strong>' + self.name() + '</strong>)?'),
                callback: function () {
                    $osf.postJSON(ctx.node.urls.api + 'remove_citation/',
                        {'id': self.id},
                        function() {
                            var index = parent.citations.indexOf(self);
                            parent.citations.splice(index, 1);
                            if (parent.editing()) {
                                parent.editing(false);
                            }
                        },
                        function() {
                            $osf.growl('Error:',
                                'An unexpected error has occurred.  Please try again later.  If problem persists contact <a href="mailto: support@cos.io">support@cos.io</a>', 'danger'
                            );
                        });
                },
                buttons:{
                    confirm:{
                        label:'Delete',
                        className:'btn-danger'
                    }
                }
            });
        }
    };

    self.cancel = function(parent) {
        if (self.originalValues === undefined) {
            var index = parent.citations.indexOf(self);
            parent.citations.splice(index, 1);
        }
        else {
            self.name(self.originalValues.name);
            self.text(self.originalValues.text);
            self.view('view');
        }
        parent.editing(false);
        self.messages([]);
    };

    self.save = function(parent) {
        self.messages([]);
        if (self.name() === undefined || self.name().length === 0) {
            self.messages.push('\'Name\' is required');
        }
        if (self.text() === undefined || self.text().length === 0) {
            self.messages.push('\'Citation\' is required');
        }
        for (var i = 0, citation; citation = parent.citations()[i]; i++) {
            if (citation !== self) {
                if (citation.name() === self.name()) {
                    self.messages.push('There is already an alternative citation named \'' + self.name() + '\'');
                }
                if (citation.text() === self.text()) {
                    self.messages.push('Citation matches \'' + citation.name() + '\'');
                }
            }
        }
        if (self.messages().length === 0) {
            $osf.postJSON(ctx.node.urls.api + 'edit_citation/',
                {'name': self.name(), 'text': self.text(), 'id': self.id},
                function(data) {
                    parent.editing(false);
                    self.view('view');
                    if (data !== null) {
                        self.id = data;
                    }
                    if (self.originalValues !== undefined) {
                        self.originalValues.name = self.name();
                        self.originalValues.text = self.text();
                    }
                    else {
                        self.originalValues = {
                            name: self.name(),
                            text: self.text()
                        };
                    }
                },
                function(data) {
                    if (data.status === 400) {
                        if (data.responseJSON.nameExists === true) {
                            self.messages.push('There is already an alternative citation named \'' + self.name() + '\'');
                        }
                        if (data.responseJSON.matchingCitations.length > 0) {
                            self.messages.push('Citation matches \'' + data.responseJSON.matchingCitations.join('\', \'') + '\'');
                        }
                    }
                    else {
                        $osf.growl('Error:',
                            'An unexpected error has occurred.  Please try again later.  If problem persists contact <a href="mailto: support@cos.io">support@cos.io</a>', 'danger'
                        );
                    }
                });
        }
    };

    self.edit = function(parent) {
        if (parent !== undefined) {
            parent.editing(true);
        }
        self.view('edit');
    };
    self.init();
};

ViewModel.prototype.fetch = function() {
    var self = this;
    var citationRequest = $.ajax(ctx.node.urls.api + 'citation/');
    var styleRequests = [
        $.ajax(BASE_URL + STYLES.apa),
        $.ajax(BASE_URL + STYLES.mla),
        $.ajax(BASE_URL + STYLES.chicago)
    ];
    var requests = [citationRequest].concat(styleRequests);
    $.when.apply(self, requests).done(function(data, apa, mla, chicago) {
        self.apa(formatCitation(apa[0], data[0], 'text'));
        self.mla(formatCitation(mla[0], data[0], 'text'));
        self.chicago(formatCitation(chicago[0], data[0], 'text'));
    }).fail(function() {
        console.log('Could not load citations');
    });
};

var CitationList = function(selector, citations, user) {
    this.viewModel = new ViewModel(citations, user);
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.fetch();
};

module.exports = CitationList;
