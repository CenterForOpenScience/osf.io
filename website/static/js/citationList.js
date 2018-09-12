'use strict';

var $ = require('jquery');
var ko = require('knockout');
require('knockout.validation');
var $osf = require('./osfHelpers');
var citations = require('./citations');
var bootbox = require('bootbox');
var oop = require('js/oop');
var makeClient = require('js/clipboard');

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

var ViewModel = oop.defclass({
     constructor: function() {
        var self = this;
        self.loading = ko.observable(true);
        self.customCitation = ko.observable('');
        self.initialCustomCitation = ko.observable();
        self.apa = ko.observable();
        self.mla = ko.observable();
        self.chicago = ko.observable();
        self.showEdit =  ko.observable(false);
        self.page = ko.computed(function () {
            if(self.loading()){
                return 'loading';
            } else if(self.showEdit()) {
                return 'edit';
            } else if(self.customCitation() === '') {
                return 'standard';
            } else {
                return 'custom';
            }
        });
        self.nodeType = ko.computed(function () {
            return ctx.node.isRegistration ? 'registrations' : 'nodes';
        });

        self.disableRemove = ko.computed(function () {
            return self.initialCustomCitation() === '';
        });

        self.disableSave = ko.computed(function () {
            return self.customCitation() === '' || self.initialCustomCitation() === self.customCitation();
        });

        makeClient($('#custom-citation-copy-button')[0]);
    },
    showEditBox: function() {
        var self = this;
        self.showEdit(true);
        self.initialCustomCitation(self.customCitation());
    },
    cancelCitation: function() {
        var self = this;
        self.showEdit(false);
        self.customCitation(self.initialCustomCitation());
    },
    saveCitation: function() {
        var self = this;
        self.loading(true);
        self.updateCustomCitation();
    },
    clearCitation: function() {
        var self = this;
        if(self.customCitation() !== '') {
            self.customCitation('');
            self.loading(true);
            self.updateCustomCitation();
        } else {
            self.showEdit(false);
        }
    },
    updateCustomCitation: function() {
        var self = this;
        var payload = {
            'data': {
                'id' : ctx.node.id,
                'type' :  self.nodeType(),
                'attributes' : {
                    'custom_citation': self.customCitation()
                 }
            }
        };
        self.showEdit(false);
        $osf.ajaxJSON(
            'PATCH',
            ctx.apiV2Prefix  + self.nodeType() + '/' + ctx.node.id + '/',
            {
                isCors: true,
                data: payload
            }
        ).done(function(data) {
            if (!self.customCitation()) {
		        self.fetch();
		    }
		    self.loading(false);

        }).fail(function() {
            $osf.growl('Error', 'Your custom citation not updated. Please refresh the page and try ' +
            'again or contact ' + $osf.osfSupportLink() + ' if the problem persists.', 'danger');
        });
    },
    fetch: function() {
        var self = this;
        $osf.ajaxJSON(
            'GET',
            ctx.apiV2Prefix  +  self.nodeType() + '/' + ctx.node.id + '/',
            {isCors: true}
        ).done(function(data) {
            self.customCitation(data.data.attributes.custom_citation);
            if(!self.customCitation()) {
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
                });
            }
        }).fail(function() {
            console.log('Could not load citations');
        }).always(function() {
            self.loading(false);
        });

    }
});

var CitationList = function(selector) {
    this.viewModel = new ViewModel();
    $osf.applyBindings(this.viewModel, selector);
    this.viewModel.fetch();
};

module.exports = CitationList;
