'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('osfHelpers');
var citations = require('citations');

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

var ViewModel = function() {
    this.apa = ko.observable();
    this.mla = ko.observable();
    this.chicago = ko.observable();
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

var CitationList = function(selector) {
    this.viewModel = new ViewModel();
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.fetch();
};

module.exports = CitationList;
