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

    if (citation !== undefined) {
        self.name = ko.observable(citation.name);
        self.text = ko.observable(citation.text);
        self.view = ko.observable(view);
        self.originalValues = {
            name: citation.name,
            text: citation.text
        };
    }
    else {
        self.view = ko.observable('edit');
        self.name = ko.observable();
        self.text = ko.observable();
    }

    self.removeSelf = function(parent) {
        if (self.originalValues !== undefined) {
            bootbox.confirm({
                title: 'Delete citation?',
                message: ('Are you sure you want to remove this citation (<strong>' + self.name() + '</strong>)?'),
                callback: function () {
                    console.log('removed');
                },
                buttons:{
                    confirm:{
                        label:'Delete',
                        className:'btn-danger'
                    }
                }
            });
        }
        var index = parent.citations.indexOf(self);
        parent.citations.splice(index, 1);
        if (parent.editing()) {
            parent.editing(false);
        }
    };

    self.cancel = function(parent) {
        if (self.originalValues === undefined) {
            self.removeSelf(parent);
        }
        else {
            self.name(self.originalValues.name);
            self.text(self.originalValues.text);
            parent.editing(false);
            self.view('view');
        }
    };

    self.save = function(parent) {
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

        parent.editing(false);
        self.view('view');
    };

    self.edit = function(parent) {
        parent.editing(true);
        self.view('edit');
    };
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
