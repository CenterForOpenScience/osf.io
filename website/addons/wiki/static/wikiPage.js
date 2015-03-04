'use strict';
var ko = require('knockout');
var $ = require('jquery');
var $osf = require('osfHelpers');

var mathrender = require('mathrender');
var md = require('markdown').full;
var mdQuick = require('markdown').quick;
var diffTool = require('diffTool');

var THROTTLE = 500;

//<div id="preview" data-bind="mathjaxify">
ko.bindingHandlers.mathjaxify = {
    update: function(element, valueAccessor, allBindingsAccessor, data, context) {
        var vm = context.$data;
        //Need to unwrap the data in order for KO to know it's changed.
        ko.unwrap(valueAccessor());

        if(vm.allowMathjaxification() && vm.allowFullRender()) {
            mathrender.mathjaxify('#' + element.id);
        }
    }
};


function ViewWidget(visible, version, viewText, rendered, contentURL, allowMathjaxification, allowFullRender, editor) {
    var self = this;
    self.version = version;
    self.viewText = viewText; // comes from EditWidget.viewText
    self.rendered = rendered;
    self.visible = visible;
    self.allowMathjaxification = allowMathjaxification;
    self.editor = editor;
    self.allowFullRender = allowFullRender;
    self.renderTimeout = null;
    self.displaySource = ko.observable('');
    self.debouncedAllowFullRender = $osf.debounce(function() {
        self.allowFullRender(true);
    }, THROTTLE);

    self.renderMarkdown = function(rawContent){
        if(self.visible()) {
            if (self.allowFullRender()) {
                return md.render(rawContent);
            } else {
                return mdQuick.render(rawContent);
            }
        } else {
            return '';
        }
    };

    if (typeof self.editor !== 'undefined') {
        self.editor.on('change', function () {
            if(self.version() === 'preview') {
                // Quick render
                self.allowFullRender(false);

                // Full render
                self.debouncedAllowFullRender();
            }
        });
    } else {
        self.allowFullRender(true);
    }

    self.displayText =  ko.computed(function() {
        self.allowFullRender();
        var requestURL;
        if (typeof self.version() !== 'undefined') {
            if (self.version() === 'preview') {
                self.rendered(self.renderMarkdown(self.viewText()));
                self.displaySource(self.viewText());
            } else {
                if (self.version() === 'current') {
                    requestURL = contentURL;
                } else {
                    requestURL= contentURL + self.version();
                }
                var request = $.ajax({
                    url: requestURL
                });

                request.done(function (resp) {
                    if(self.visible()) {
                        var rawContent = resp.wiki_content || '*No wiki content*';
                        if (resp.wiki_rendered) {
                            // Use pre-rendered python, if provided. Don't mathjaxify
                            self.allowMathjaxification(false);
                            self.rendered(resp.wiki_rendered);

                        } else {
                            // Render raw markdown
                            self.allowMathjaxification(true);
                            self.rendered(self.renderMarkdown(rawContent));
                        }
                        self.displaySource(rawContent);
                    }
                });
            }
        } else {
            self.displaySource('');
        }
    });
}

    // currentText comes from ViewWidget.displayText
function CompareWidget(visible, compareVersion, currentText, rendered, contentURL) {
    var self = this;

    self.compareVersion = compareVersion;
    self.currentText = currentText;
    self.rendered = rendered;
    self.visible = visible;
    self.contentURL = contentURL;
    self.compareSource = ko.observable('');

    self.compareText = ko.computed(function() {
        var requestURL;
        if (self.compareVersion() === 'current') {
            requestURL = self.contentURL;
        } else {
            requestURL= self.contentURL + self.compareVersion();
        }
        var request = $.ajax({
            url: requestURL
        });
        request.done(function (resp) {
            var rawText = resp.wiki_content;
            self.compareSource(rawText);
        });

    });

    self.compareOutput = ko.computed(function() {
        var output = diffTool.diff(self.compareSource(), self.currentText());
        self.rendered(output);
        return output;
    }).extend({ notify: 'always' });

}


var defaultOptions = {
    editVisible: false,
    viewVisible: true,
    compareVisible: false,
    menuVisible: true,
    canEdit: true,
    viewVersion: 'current',
    compareVersion: 'previous',
    urls: {
        content: '',
        draft: '',
        page: ''
    },
    metadata: {}
};

function ViewModel(options){
    var self = this;

    // enabled?
    self.editVis = ko.observable(options.editVisible);
    self.viewVis = ko.observable(options.viewVisible);
    self.compareVis = ko.observable(options.compareVisible);
    self.menuVis = ko.observable(options.menuVisible);

    self.pageTitle = $(document).find("title").text();

    self.compareVersion = ko.observable(options.compareVersion);
    self.viewVersion = ko.observable(options.viewVersion);
    self.draftURL = options.urls.draft;
    self.contentURL = options.urls.content;
    self.pageURL = options.urls.page;
    self.editorMetadata = options.metadata;
    self.canEdit = options.canEdit;

    self.viewText = ko.observable('');
    self.renderedView = ko.observable('');
    self.renderedCompare = ko.observable('');
    self.allowMathjaxification = ko.observable(true);
    self.allowFullRender = ko.observable(true);
    self.viewVersionDisplay = ko.computed(function() {
        var versionString = '';
        if (self.viewVersion() === 'preview') {
            versionString = 'Live preview';
        } else if (self.viewVersion() === 'current'){
            versionString = 'Current version';
        } else if (self.viewVersion() === 'previous'){
            versionString = 'Previous version';
        } else {
            versionString = 'Version ' + self.viewVersion();
        }
        return versionString;
    });

    self.currentURL = ko.computed(function() {

        // Do not change URL for incompatible browsers
        if (typeof window.history.replaceState === 'undefined') {
            return;
        }

        var url = self.pageURL;

        // Default view is special cased
        if (!self.editVis() && self.viewVis() && self.viewVersion() === 'current' && !self.compareVis() && self.menuVis()) {
            window.history.replaceState({}, '', url);
            return;
        }

        var paramPrefix = '?';

        if (self.editVis()) {
            url += paramPrefix + 'edit';
            paramPrefix = '&';
        }
        if (self.viewVis()) {
            url += paramPrefix + 'view';
            paramPrefix = '&';
            if  ((!self.editVis() && self.viewVersion() !== 'current' ) ||
                 (self.editVis() && self.viewVersion() !== 'preview')) {
                url += '=' + self.viewVersion();
            }
        }
        if (self.compareVis()) {
            url += paramPrefix + 'compare';
            paramPrefix = '&';
            if (self.compareVersion() !== 'previous'){
                url += '=' + self.compareVersion();
            }
        }
        if (self.menuVis()) {
            url += paramPrefix + 'menu';
        }

        window.history.replaceState({}, self.pageTitle, url);
    });


    if(self.canEdit) {
        self.editor = ace.edit('editor'); // jshint ignore: line

        var ShareJSDoc = require('addons/wiki/static/ShareJSDoc.js');
        self.editVM = new ShareJSDoc(self.draftURL, self.editorMetadata, self.viewText, self.editor);
    }
    self.viewVM = new ViewWidget(self.viewVis, self.viewVersion, self.viewText, self.renderedView, self.contentURL, self.allowMathjaxification, self.allowFullRender, self.editor);
    self.compareVM = new CompareWidget(self.compareVis, self.compareVersion, self.viewVM.displaySource, self.renderedCompare, self.contentURL);

    var bodyElement = $('body');
    bodyElement.on('togglePanel', function (event, panel, display) {
        // Update self.editVis, self.viewVis, or self.compareVis in viewmodel
        self[panel + 'Vis'](display);

        //URL needs to be a computed observable, and this should just update the panel states, which will feed URL

        // Switch view to correct version
        if (panel === 'edit') {
            if (display) {
                self.viewVersion('preview');
            } else if (self.viewVersion() === 'preview') {
                self.viewVersion('current');
            }
        } else if (panel === 'view') {
            if(!display && self.compareVis() && self.editVis()){
                self.viewVersion('preview');
            }
        }
    });

    bodyElement.on('toggleMenu', function(event, menuVisible) {
        self.menuVis(menuVisible);
    });
}



var WikiPage = function(selector, options) {
    var self = this;
    self.options = $.extend({}, defaultOptions, options);

    this.viewModel = new ViewModel(self.options);
    $osf.applyBindings(self.viewModel, selector);
};

module.exports = WikiPage;

