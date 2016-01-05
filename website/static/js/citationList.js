'use strict';

var $ = require('jquery');
var ko = require('knockout');
require('knockout.validation');
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
        return new AlternativeModel(item, 'view', self);
    }));

    self.editing = ko.observable(false);

    self.addAlternative = function() {
        self.citations.push(new AlternativeModel(null, null, self));
        self.editing(true);
    };
    self.apa = ko.observable();
    self.mla = ko.observable();
    self.chicago = ko.observable();
};

var AlternativeModel = function(citation, view, parent) {
    var self = this;

    self.init = function() {
        if (!!citation) {
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

        self.name.extend({
            required: {
                message: '"Citation name" is required'
            },
            validation: {
                validator: function() {
                    for (var i = 0, citation; citation = parent.citations()[i]; i++) {
                        if (citation !== self) {
                            if (citation.name() === self.name()) {
                                return false;
                            }
                        }
                    }
                    return true;
                },
                'message': function() {
                    return 'There is already a citation named \'' + self.name() + '\'';
                }
            }
        });
        self.text.extend({
            required: {
                message: '"Citation" is required'
            },
            validation: {
                validator: function() {
                    self.matchesText = [];
                    for (var i = 0, citation; citation = parent.citations()[i]; i++) {
                        if (citation !== self) {
                            if (citation.text() === self.text()) {
                                self.matchesText.push(citation.name());
                            }
                        }
                    }
                    return self.matchesText.length === 0;
                },
                'message': function() {
                    return 'Citation matches \'' + self.matchesText.join(', ') + '\'';
                }
            }
        });
    };

    self.removeSelf = function(parent) {
        if (self.originalValues !== undefined) {
            bootbox.confirm({
                title: 'Delete citation?',
                message: ('Are you sure you want to remove this citation (<strong>' + $osf.htmlEscape(self.name()) + '</strong>)?'),
                callback: function (confirmed) {
                    if (confirmed) {
                        $osf.ajaxJSON('DELETE', $osf.apiV2Url('nodes/' + ctx.node.id + '/citations/' + self.id + '/'), {isCors: true}).done(function(response) {
                            var index = parent.citations.indexOf(self);
                            parent.citations.splice(index, 1);
                            if (parent.editing()) {
                                parent.editing(false);
                            }
                        }).fail(function(response){
                            $osf.growl('Error:',
                                'An unexpected error has occurred.  Please try again later.  If problem persists contact <a href="mailto: support@osf.io">support@osf.io</a>', 'danger'
                            );
                        });
                    }
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
    };

    self.save = function(parent) {
        if (self.isValid()) {
            var url = $osf.apiV2Url('nodes/' + ctx.node.id + '/citations/');
            var payload = {};
            var method = 'POST';
            payload.data = {
                'type': 'citations',
                'attributes': {
                    'name': self.name(),
                    'text': self.text()
                }
            };
            if (self.id !== undefined) {
                url += self.id + '/';

                payload.data.attributes.id = self.id;
                method = 'PUT';
            }
            $osf.ajaxJSON(method, url, {data: payload, isCors: true}).done(function (response) {
                var data = response.data;
                parent.editing(false);
                self.view('view');
                self.id = data.id;
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
            }).fail(function (response) {
                $osf.growl('Error:',
                    'An unexpected error has occurred.  Please try again later.  If problem persists contact <a href="mailto: support@osf.io">support@osf.io</a>', 'danger'
                );
            });
        }
        else {
            self.showMessages(true);
        }
    };

    self.edit = function(parent) {
        if (parent !== undefined) {
            parent.editing(true);
        }
        self.view('edit');
    };
    self.init();

    var validated = ko.validatedObservable(self);

    self.isValid = ko.computed(function() {
        return validated.isValid();
    });

    self.showMessages = ko.observable(false);
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
