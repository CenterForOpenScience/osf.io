webpackJsonp([39],{

/***/ 0:
/***/ function(module, exports, __webpack_require__) {

'use strict';
var $ = __webpack_require__(38);
var ko = __webpack_require__(48);
var bootbox = __webpack_require__(138);
var $osf = __webpack_require__(47);

var language = __webpack_require__(164).registrations;

var MetaData = __webpack_require__(409);
var ctx = window.contextVars;

__webpack_require__(412);

/**
    * Unblock UI and display error modal
    */
function registrationFailed() {
    $osf.unblock();
    bootbox.alert({
        title : 'Registration failed',
        message : 'There was a problem completing your registration right now. Please try again later. If this should not have occurred and the issue persists, please report it to <a href=\"mailto:support@osf.io\">support@osf.io</a> ',
        buttons:{
            ok:{
                label:'Close',
                className:'btn-default'
            }
        }
    } );
}

function registerNode(data) {

    // Block UI until request completes
    $osf.block();

    // POST data
    $.ajax({
        url:  ctx.node.urls.api + 'register/' + ctx.regTemplate + '/',
        type: 'POST',
        data: JSON.stringify(data),
        contentType: 'application/json',
        dataType: 'json'
    }).done(function(response) {
        if (response.status === 'initiated') {
            $osf.unblock();
            window.location.assign(response.urls.registrations);
        }
        else if (response.status === 'error') {
            registrationFailed();
        }
    }).fail(function() {
        registrationFailed();
    });

    // Stop event propagation
    return false;

}

$(document).ready(function() {

    // Don't submit form on enter; must use $.delegate rather than $.on
    // to catch dynamically created form elements
    $('#registration_template').delegate('input, select', 'keypress', function(event) {
        return event.keyCode !== 13;
    });

    var registrationViewModel = new MetaData.ViewModel(
        ctx.regSchema,
        ctx.registered,
        [ctx.node.id].concat(ctx.node.children)
    );
    // Apply view model
    ko.applyBindings(registrationViewModel, $('#registration_template')[0]);
    registrationViewModel.updateIdx('add', true);

    if (ctx.registered) {
        registrationViewModel.unserialize(ctx.regPayload);
    }

    $('#registration_template form').on('submit', function() {

        // If embargo is requested, verify its end date, and inform user if date is out of range
        if (registrationViewModel.embargoAddon.requestingEmbargo()) {
            if (!registrationViewModel.embargoAddon.isEmbargoEndDateValid()) {
                registrationViewModel.continueText('');
                $osf.growl(
                    language.invalidEmbargoTitle,
                    language.invalidEmbargoMessage,
                    'warning'
                );
                $('#endDatePicker').focus();
                return false;
            }
        }
        // Serialize responses
        var serialized = registrationViewModel.serialize(),
            data = serialized.data,
            complete = serialized.complete;

        // Clear continue text and stop if incomplete
        if (!complete) {
            registrationViewModel.continueText('');
            return false;
        }

        $osf.block();
        $.ajax({
            url: ctx.node.urls.api + 'beforeregister/',
            contentType: 'application/json',
            success: function(response) {
                var preRegisterWarnings = function() {
                    bootbox.confirm(
                        {
                            size: 'large',
                            message : $osf.joinPrompts(response.prompts, '<h4>'+ language.registerConfirm + '</h4>'),
                            callback: function(result) {
                                if (result) {
                                    registerNode(data);
                                }
                            },
                            buttons:{
                                confirm:{
                                    label:'Register'
                                }
                           }
                        }
                    );
                };
                var preRegisterErrors = function(confirm, reject) {
                    bootbox.confirm({
                        message: ($osf.joinPrompts(
                            response.errors,
                            '<h4>Before you continue...</h4>'
                        ) + '<hr /> ' + language.registerSkipAddons),
                        callback: function (result) {
                            if (result) {
                                confirm();
                            }
                        },
                        buttons:{
                            confirm:{
                                label:'Continue'
                            }
                        }
                    });
                };

                if (response.errors && response.errors.length) {
                    preRegisterErrors(preRegisterWarnings);
                }
                else if (response.prompts && response.prompts.length) {
                    preRegisterWarnings();
                } 
                else {
                    registerNode(data);
                }
            }
        }).always(function() {
            $osf.unblock();
        });
        return false;
    });
});


/***/ },

/***/ 164:
/***/ function(module, exports) {

var SUPPORT_EMAIL = 'support@osf.io';
var SUPPORT_LINK = '<a href="mailto: ' + SUPPORT_EMAIL + '">' + SUPPORT_EMAIL + '</a>';

var REFRESH_OR_SUPPORT = 'Please refresh the page and try again or contact ' + SUPPORT_LINK + ' if the problem persists.';

module.exports = {
    // TODO
    makePublic: null,
    makePrivate: null,
    registrations: {
        registrationFailed: 'Registration failed. If this problem persists, please contact ' + SUPPORT_EMAIL + '.',
        invalidEmbargoTitle: 'Invalid embargo end date',
        invalidEmbargoMessage: 'Please choose a date more than two days, but less than four years, from today.',
        registerConfirm: 'Are you sure you want to register this project?',
        registerSkipAddons: 'If you choose to continue with the registration at this time we will exclude the contents of any addons that are not copyable. These files will not appear in the final registration.'
    },
    Addons: {
        dataverse: {
            userSettingsError: 'Could not retrieve settings. Please refresh the page or ' +
                'contact <a href="mailto: ' + SUPPORT_EMAIL + '">' + SUPPORT_EMAIL + '</a> if the ' +
                'problem persists.',
            deauthError: 'Could not disconnect the Dataverse account at this time.',
            authError: 'Sorry, but there was a problem connecting to that instance of Dataverse. It ' +
                'is likely that the instance hasn\'t been upgraded to Dataverse 4.0. If you ' +
                'have any questions or believe this to be an error, please contact ' +
                'support@osf.io.',
            authInvalid: 'Your Dataverse API token is invalid.',
            authSuccess: 'Your Dataverse account was linked.',
            datasetDeaccessioned: 'This dataset has already been deaccessioned on the Dataverse ' +
                'and cannot be connected to the OSF.',
            forbiddenCharacters: 'This dataset cannot be connected due to forbidden characters ' +
                'in one or more of the dataset\'s file names. This issue has been forwarded to our ' +
                'development team.',
            setDatasetError: 'Could not connect to this dataset.',
            widgetInvalid: 'The credentials associated with this Dataverse account ' +
                'appear to be invalid.',
            widgetError: 'There was a problem connecting to the Dataverse.'
        },
        dropbox: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: 'Are you sure you want to disconnect the Dropbox account? ' +
                'This will revoke access to Dropbox for all projects you have ' +
                'associated with this account.',
            deauthError: 'Could not disconnect Dropbox account at this time',
        },
        figshare: {
            confirmDeauth: 'Are you sure you want to disconnect the figshare account? ' +
                'This will revoke access to figshare for all projects you have ' +
                'associated with this account.',
        },
        // TODO
        github: {
            confirmDeauth: 'Are you sure you want to disconnect the GitHub account? ' +
                'This will revoke access to GitHub for all projects you have ' +
                'associated with this account.',
        },
        s3: {
            confirmDeauth: 'Are you sure you want to disconnect the S3 account? ' +
                'This will revoke access to S3 for all projects you have ' +
                'associated with this account.',
        },
        box: {
            // Shown on clicking "Delete Access Token" for dropbox
            confirmDeauth: 'Are you sure you want to disconnect the Box account? ' +
                'This will revoke access to Box for all projects you have ' +
                'associated with this account.',
            deauthError: 'Could not disconnect the Box account at this time',
        },
        googledrive: {
          // Shown on clicking "Delete Access Token" for googledrive
            confirmDeauth: 'Are you sure you want to disconnect the Google Drive account? ' +
                'This will revoke access to Google Drive for all projects you have ' +
                'associated with this account.',
            deauthError: 'Could not disconnect the Google Drive account at this time',
        }
    },
    apiOauth2Application: {
        discardUnchanged: 'Are you sure you want to discard your unsaved changes?',
        deactivateConfirm: 'Are you sure you want to deactivate this application for all users and revoke all access tokens? This cannot be reversed.',
        deactivateError: 'Could not deactivate application. Please wait a few minutes and try again, or contact ' + SUPPORT_LINK + ' if the problem persists.',
        dataFetchError: 'Data not loaded. ' + REFRESH_OR_SUPPORT,
        dataListFetchError: 'Could not load list of developer applications at this time. ' + REFRESH_OR_SUPPORT,
        dataSendError: 'Error sending data to the server: check that all fields are valid, or contact ' + SUPPORT_LINK + ' if the problem persists.',
        creationSuccess: 'Successfully registered new application',
        dataUpdated: 'Application data updated'
    }
};


/***/ },

/***/ 409:
/***/ function(module, exports, __webpack_require__) {

/* WEBPACK VAR INJECTION */(function($) {/**
 * Knockout models for controlling metadata; bound to HTML in
 * website/templates/metadata/metadata_*.mako
 */
var ko = __webpack_require__(48);
var registrationEmbargo = __webpack_require__(410);

var MetaData = (function() {

    var SEPARATOR = '-';
    var IDX_SEPARATOR = ':';
    var TPL_REGEX = /{{(.*?)}}/;

    ko.bindingHandlers.item = {
        init: function(element, valueAccessor) {
            var model = ko.utils.unwrapObservable(valueAccessor());
            ko.renderTemplate(model.type, model, {}, element, 'replaceNode');
        }
    };

    // Initialize unique index for Content objects
    var uid = 1;

    function Content(content, $parent, $root, $ctx, refresh) {

        if (!content) {
            return;
        }

        var self = this;

        self.$parent = $parent;
        self.$root = $root;
        self.$ctx = $ctx;

        // Give each Content a unique index for tracking
        self.uid = uid;
        self.uidFmt = 'metadata-' + self.uid;
        uid++;

        // Copy content to self
        $.extend(self, content);

        // Set up each
        if ('each' in self && content.repeatType === 'each') {
            if (typeof(self.each) === 'string') {
                self._contentsObservable = null;
                self._contentsData = {};
                self.contents = ko.computed(function() {
                    if (!self._contentsObservable) {
                        self.$root._refresh();
                        var eachSplit = self.each.split('.');
                        var eachContent = self.getKey(eachSplit[1]);
                        if (eachContent) {
                            self._contentsObservable = eachContent.contents;
                        }
                    }
                    if (self._contentsObservable) {
                        var contents = $.map(self._contentsObservable(), function(data) {
                            if (!(data.uid in self._contentsData)) {
                                var newContent = delegateContent(self._template, self, self.$root, data, false);
                                newContent.updateIdx('add', false);
                                self._contentsData[data.uid] = newContent;
                            }
                            return self._contentsData[data.uid];
                        });
                        self.updateIdx('add', true);
                        return contents;
                    }
                    return [];
                });
            } else {
                $.each(self.each, function(idx, data) {
                    self.addRepeat(data, false);
                });
                if (self.$root.pages) {
                    self.updateIdx('add');
                }
            }
        }

        // Impute defaults
        self.displayRules = self.displayRules || {};
        self.canRepeat = self.canRepeat || false;
        self.minRepeat = typeof(self.minRepeat) !== 'undefined' ? self.minRepeat : 1;
        self.maxRepeat = self.maxRepeat || null;

        $.each(['id', 'title', 'label', 'caption', 'value'], function(idx, field) {
            // todo: recurse over iterables
            if (self[field] && typeof(self[field]) === 'string' && self[field].match(TPL_REGEX)) {
                self.contextComputed(field);
            }
        });

        // Process display rules
        self.visible = ko.computed(function() {
            self.$root._refresh();
            var _visible = true;
            $.each(self.displayRules, function(key, value) {
                var model = self.getKey(key);
                var modelValue = model ? model.value() : null;
                if (modelValue !== value) {
                    _visible = false;
                    return false;
                }
            });
            return _visible;
        });

        // Optionally refresh
        if (refresh) {
            $root.refresh();
        }

    }

    Content.prototype = {

        // todo: review & test
        contextComputed: function(field) {
            var self = this;
            var _original = self[field];
            self[field] = ko.computed(function() {
                value = _original;
                while (match = value.match(TPL_REGEX)) {
                    ctxSplit = match[1].split('.');
                    if (ctxSplit[0] === '$ctx') {
                        cntValue = self;
                        ctxValue = self.$ctx;
                        $.each(ctxSplit.slice(1), function(idx, key) {
                            if (key === '$parent') {
                                cntValue = cntValue.$parent;
                                ctxValue = cntValue.$ctx;
                            } else {
                                ctxValue = ctxValue[key];
                            }
                        });  // jshint ignore:line
                    } else if (ctxSplit[0] === '$svy') {
                        model = self.getKey(ctxSplit[1]);
                        ctxValue = model ? model.value() : '';
                    }
                    value = value.replace(TPL_REGEX, ko.utils.unwrapObservable(ctxValue));
                }
                return value;
            });
        },

        scrollToTop: function() {
            $('html, body').animate({
                scrollTop: $('#' + this.uidFmt).offset().top
            });
        },

        /*
         * Get index of current page or null if not found.
         */
        getPage: function() {
            var self = this;
            var cursor = self;
            while (cursor) {
                if (!cursor.type) {
                    return self.$root.pages.indexOf(cursor);
                }
                cursor = cursor.$parent;
            }
            return null;
        },

        /*
         * Determine whether content is displayed; content whose visible
         * computed is true will not be displayed if contained by a parent
         * content whose visible is false.
         */
        isDisplayed: function() {
            var cursor = this;
            while (cursor) {
                if (cursor.visible && !cursor.visible()) {
                    return false;
                }
                cursor = cursor.$parent;
            }
            return true;
        },

        /*
         *
         */
        getKey: function(key) {
            var child = this;
            while (child.$parent) {
                child = child.$parent;
                if (child.observedData && key in child.observedData) {
                    return child.observedData[key];
                }
            }
            return this.$root.observedData[key];
        },

        getIdx: function() {
            return this.$parent.contents().indexOf(this);
        },

        updateIdx: function(action, refresh) {

            var idx = [],
                child = this,
                key;

            if (this.contents) {
                $.each(this.contents(), function(idx, content) {
                    content.updateIdx(action, false);
                });
            }

            while (child) {
                if (child.$parent && child.$parent.repeatSection) {
                    idx.unshift(ko.utils.unwrapObservable(child.id) + IDX_SEPARATOR + child.getIdx());
                    var _idx = child.getIdx();
                } else if (!child.type) {
//                        idx.unshift('page:' + this.$root.pages.indexOf(child));
//                        var _idx = this.$root.pages.indexOf(child);
//                        if (_idx != -1) {
//                            idx.unshift('page:' + _idx);
//                        }
                } else if (this.type === 'section' || !child.repeatSection) {
                    idx.unshift(ko.utils.unwrapObservable(child.id));
                }
                if (child.$parent && child.$parent.observedData) {
                    key = idx.join(SEPARATOR);
                    if (action === 'add') {
                        child.$parent.observedData[key] = this;
                    } else if (action === 'remove') {
                        delete child.$parent.observedData[key];
                    }
                }
                child = child.$parent;
            }

            key = idx.join(SEPARATOR);
            if (action === 'add') {
                this.$root.observedData[key] = this;
            } else if (action === 'remove') {
                delete this.$root.observedData[key];
            }

            if (refresh) {
                this.$root.refresh();
            }

        },

        addRepeat: function(data, update) {
            var content = delegateContent(this._template, this, this.$root, data);
            this.contents.push(content);
            if (update) {
                content.updateIdx('add');
            }
        },

        removeRepeat: function() {
            this.$parent.updateIdx('remove');
            var parentIdx = this.getIdx();
            this.$parent.contents.splice(parentIdx, 1);
            this.$parent.updateIdx('add');
        },

        repeatCount: function() {
            return this.contents ? this.contents().length : 0;
        }

    };


    function Section() {

        var self = this;
        Content.apply(this, arguments);

        var tmpContents = self.contents;
        self.contents = ko.observableArray();
        $.each(tmpContents, function(idx, content) {
            self.contents.push(
                delegateContent(content, self, self.$root, null, false)
            );
        });

        if (self.repeatType === 'repeat') {
            self.initRepeat = self.initRepeat || 1;
            for (var i=0; i<self.initRepeat; i++) {
                self.addRepeat(null, false);
            }
        }

        self.observedData = {};

    }

    Section.prototype = Object.create(Content.prototype);

    function Item() {

        var self = this;
        Content.apply(this, arguments);

        if ('options' in self && typeof(self.options) === 'string') {
            var eachSplit = self.options.split('.');
            self._optionsOriginal = self.options;
            self._optionsObservable = null;
            self.options = ko.computed(function() {
                if (!self._optionsObservable) {
                    self.$root._refresh();
                    var optSplit = self._optionsOriginal.split('.');
                    var optContent = self.getKey(optSplit[1]);
                    if (optContent) {
                        if (optContent.contents) {
                            self._optionsObservable = optContent.contents;
                        } else if (optContent.value) {
                            self._optionsObservable = optContent.value;
                        }
                    }
                }
                if (self._optionsObservable) {
                    return $.map(self._optionsObservable(), function(option) {
                        if (option.value) {
                            return option.value();
                        }
                        return option;
                    });
                }
                return [];
            });
        }

        // Set up observable on value
        if (self.multiple || self.type === 'checkbox') {
            self.value = ko.observableArray(self.value || []);
        } else {
            self.value = ko.observable(ko.utils.unwrapObservable(self.value) || '');
        }

        // Impute item-level defaults
        self.required = self.required || false;
        self.validation = self.validation || [];
        self.disable = self.disable || false;
        self.helpText = self.helpText || '';
        self.multiple = self.multiple || false;

        self.isValid = ko.computed(function() {
            return true;
        });
        self.validateText = ko.computed(function() {
            var value = self.value();
            if (!value) {
                return '';
            }
            var message = '';
            $.each(self.validation, function(idx, rule) {
                switch (rule.type) {
                    case 'regex':
                        if (!value.match(new RegExp(rule.value))) {
                            message = rule.message;
                            return false;
                        }
                }
            });
            return message;
        });

    }
    Item.prototype = Object.create(Content.prototype);
    $.extend(Item.prototype, {
        serialize: function() {
            return this.value();
        },
        unserialize: function(value) {
            this.value(value);
            return this.value() === value;
        }
    });

    function FileItem() {

        var self = this;
        Item.apply(this, arguments);

        self.node = ko.observable();
        self.nodes = self.$root.nodes;
        self.files = ko.computed(function() {
            var selectedNode = self.node();
            if (!selectedNode) {
                return [];
            }
            if (!self.$root.fileDict[selectedNode]) {
                self.$root.fileDict[selectedNode] = ko.observableArray();
                self.$root.fileDict[selectedNode]();
                $.getJSON(
                    nodeApiUrl + 'file_paths/',
                    function(response) {
                        self.$root.fileDict[selectedNode](response.files);
                    }
                );
            } else {
                return self.$root.fileDict[selectedNode]();
            }
        });

    }
    FileItem.prototype = Object.create(Item.prototype);
    $.extend(FileItem.prototype, {
        serialize: function() {
            return [this.node(), this.value()];
        },
        unserialize: function(value) {
            // Ensure that stored node is included in view model's
            // node list
            if (value[0] && this.$root.nodes.indexOf(value[0]) === -1) {
                this.$root.nodes.unshift(value[0]);
            }
            this.node(value[0]);
            this.value(value[1]);
            return this.node() === value[0] && this.value() === value[1];
        }
    });

    var contentDelegator = {
        section: Section,
        item: Item,
        file: FileItem
    };
    function delegateContent(content) {
        var type = contentDelegator[content.type] ?
            content.type :
            'item';
        var klass = contentDelegator[type];
        var args = Array.prototype.concat.apply([null], arguments);
        return new (Function.prototype.bind.apply(klass, args));  // jshint ignore: line
    }

    function Page(id, title, contents, $root) {

        var self = this;

        self.id = id;
        self.title = title;
        self.contents = ko.observableArray();
        $.each(contents, function(idx, content) {
            self.contents.push(
                delegateContent(content, self, $root)
            );
        });

        self.uidFmt = 'metadata-0';
        self.observedData = {};

    }

    Page.prototype = {

        updateIdx: function(action, refresh) {
            $.each(this.contents(), function(cidx, content) {
                content.updateIdx(action, refresh);
            });
        }

    };

    /*
     * Prepare input schema, recursively wrapping all repeatable content in
     * shell sections. This gives each repeatable content its own DOM node.
     * Also check for forbidden IDs and count frequency of each ID; no ID
     * should occur more than once.
     */
    function preprocess(content, ids) {

        // Crash if no ID
        if (!content.id) {
            throw 'ID undefined.';
        }
        // Crash if forbidden characters in IDs
        $.each([SEPARATOR, IDX_SEPARATOR], function(idx, char) {
            if (content.id.indexOf(char) !== -1) {
                throw 'Forbidden character "' + char + '" in id ' + content.id + '.';
            }
        });

        // Update ID dictionary
        ids = ids || {};
        if (ids[content.id]) {
            ids[content.id]++;
        } else {
            ids[content.id] = 1;
        }

        $.each(content.contents || [], function(idx, _content) {

            preprocess(_content, ids);

            var contentCopy = $.extend(true, {}, _content);
            contentCopy.title = null;

            if (_content.canRepeat) {
                content.contents[idx] = {
                    type: 'section',
                    title: _content.title,
                    id: _content.id,
                    minRepeat: _content.minRepeat,
                    maxRepeat: _content.maxRepeat,
                    initRepeat: _content.initRepeat,
                    repeatType: 'repeat',
                    repeatSection: true,
                    contents: [],
                    _template: contentCopy
                };
            } else if (_content.each) {
                content.contents[idx] = {
                    type: 'section',
                    each: _content.each,
                    title: _content.title,
                    id: _content.id,
                    repeatType: 'each',
                    repeatSection: true,
                    contents: [],
                    _template: contentCopy
                };
            }

        });

    }

    function ViewModel(schema, disable, nodes) {

        var self = this;
        self.nodes = nodes;
        self.fileDict = {};

        self._refresh = ko.observable();

        self.disable = disable || false;

        self.observedData = {};

        self.continueText = ko.observable('');
        self.continueFlag = ko.computed(function() {
            return self.continueText().toLowerCase() === 'register';
        });

        var ids = {};
        self.pages = $.map(schema.pages, function(page) {
            preprocess(page, ids);
            return new Page(page.id, page.title, page.contents, self);
        });
        self.npages = self.pages.length;

        // embargoAddon viewmodel component
        self.embargoAddon = new registrationEmbargo.ViewModel();

        // Check uniqueness of IDs
        $.each(ids, function(id, count) {
            if (count > 1) {
                throw 'Id "' + id + '" appeared ' + count.toString() + 'times.';
            }
        });

        self.currentIndex = ko.observable(0);

        self.currentPage = ko.computed(function(){
           return self.pages[self.currentIndex()];
        });

        self.isFirst = ko.computed(function() {
            return self.currentIndex() === 0;
        });

        self.isLast = ko.computed(function() {
            return self.currentIndex() === self.npages - 1;
        });

    }

    ViewModel.prototype = {

        getTemplate: function(data) {
            return data.type === 'section' ? 'section' : 'item';
        },

        refresh: function() {
            this._refresh(Math.random());
        },

        updateIdx: function(action) {
            $.each(this.pages, function(pidx, page) {
                page.updateIdx(action, false);
            });
            this.refresh();
        },

        scrollToTop: function() {
            $('html, body').animate({
                scrollTop: $('#meta-data-container').offset().top
            });
        },

        previous: function() {
            this.currentIndex(this.currentIndex() - 1);
            this.scrollToTop();
        },

        next: function() {
            this.currentIndex(this.currentIndex() + 1);
            this.scrollToTop();
        },

        canRemove: function(data) {
            if (data.$parent.repeatType !== 'repeat' || data.disable || this.disable) {
                return false;
            }
            var count = data.$parent.repeatCount ? data.$parent.repeatCount() : null;
            return data.$parent.repeatSection &&
                    count > data.minRepeat;
        },

        canAdd: function(data) {
            if (data.repeatType !== 'repeat' || data.disable || this.disable) {
                return false;
            }
            var count = data.repeatCount ? data.repeatCount() : null;
            var show = data.repeatSection && (
                    data.maxRepeat == null ||
                    count < data.maxRepeat
                );
            return !!show;
        },

        /*
         * Serialize form data to Object, ignoring hidden fields
         */
        serialize: function() {
            var self = this,
                data = {},
                complete = true,
                value;
            $.each(this.observedData, function(name, model) {
                if (!model.value) {
                    return true;
                }
                value = model.serialize();
                data[name] = value;
                if (complete && model.required && model.isDisplayed() && !value) {
                    self.currentIndex(model.getPage());
                    try {
                        model.scrollToTop();
                    } catch(e) {}
                    complete = false;
                }
            });
            // Add embargoAddon relevant fields
            $.extend(data, {
                'registrationChoice': self.embargoAddon.registrationChoice(),
                'embargoEndDate': self.embargoAddon.embargoEndDate().toUTCString()
            });
            return {
                data: data,
                complete: complete
            };
        },

        /*
         * Unserialize stored data to survey
         */
        unserialize: function(data) {
            var self = this;
            var nextData = {};
            $.each(data, function(key, value) {
                var keyParts = key.split(SEPARATOR);
                var current = self;
                var subIdx;
                $.each(keyParts, function(idx, keyPart) {
                    subParts = keyPart.split(IDX_SEPARATOR);
                    current = current.observedData[subParts[0]];
                    if (subParts.length > 1) {
                        if (current && current.repeatType === 'repeat') {
                            subIdx = parseInt(subParts[1]);
                            while (current.contents().length < (subIdx + 1)) {
                                current.addRepeat(null, true);
                            }
                            current = current.contents()[subIdx];
                        }
                    }
                });
                if (self.observedData[key]) {
                    var success = self.observedData[key].unserialize(value);
                    if (!success) {
                        nextData[key] = value;
                    }
                } else {
                    nextData[key] = value;
                }
            });
            if (Object.keys(nextData).length) {
                // Length of data to be unserialized hasn't changed;
                // we're stuck!
                if (Object.keys(nextData).length === Object.keys(data).length) {
                    throw 'Unserialize failed';
                }
                // Unserialize remaining data
                self.unserialize(nextData);
            }
        }

    };

    return {
        ViewModel: ViewModel,
        Content: Content
    };

}());

module.exports = MetaData;

/* WEBPACK VAR INJECTION */}.call(exports, __webpack_require__(38)))

/***/ },

/***/ 410:
/***/ function(module, exports, __webpack_require__) {

var ko = __webpack_require__(48);
var pikaday = __webpack_require__(411);

var RegistrationEmbargoViewModel = function() {

    var self = this;
    var MAKE_PUBLIC = {
        value: 'immediate',
        message: 'Make registration public immediately'
    };
    var MAKE_EMBARGO = {
        value: 'embargo',
        message: 'Enter registration into embargo'
    };
    var today = new Date();
    // TODO(hrybacki): Import min/max dates from website.settings
    var TWO_DAYS_FROM_TODAY_TIMESTAMP = new Date().getTime() + (2 * 24 * 60 * 60 * 1000);
    var FOUR_YEARS_FROM_TODAY_TIMESTAMP = new Date().getTime() + (1460 * 24 * 60 * 60 * 1000);

    self.registrationOptions = [
        MAKE_PUBLIC,
        MAKE_EMBARGO
    ];
    self.registrationChoice = ko.observable(MAKE_PUBLIC.value);

    self.pikaday = ko.observable(today);
    var picker = new pikaday(
        {
            field: document.getElementById('endDatePicker'),
            onSelect: function() {
                self.pikaday(picker.toString());
                self.isEmbargoEndDateValid();
            }
        }
    );
    self.showEmbargoDatePicker = ko.observable(false);
    self.checkShowEmbargoDatePicker = function() {
        self.showEmbargoDatePicker(self.registrationChoice() === MAKE_EMBARGO.value);
    };
    self.embargoEndDate = ko.computed(function() {
        return new Date(self.pikaday());
    });
    self.isEmbargoEndDateValid = ko.computed(function() {
        var endEmbargoDateTimestamp = self.embargoEndDate().getTime();
        return (endEmbargoDateTimestamp < FOUR_YEARS_FROM_TODAY_TIMESTAMP && endEmbargoDateTimestamp > TWO_DAYS_FROM_TODAY_TIMESTAMP);
    });
    self.requestingEmbargo = ko.pureComputed(function() {
        var choice = self.registrationChoice();
        if (choice) { return choice === MAKE_EMBARGO.value; }
    });
};

var RegistrationEmbargo = function(selector) {
    this.viewModel = new RegistrationEmbargoViewModel();
    $osf.applyBindings(this.viewModel, selector);
};

module.exports = {
    RegistrationEmbargo: RegistrationEmbargo,
    ViewModel: RegistrationEmbargoViewModel
};

/***/ },

/***/ 411:
/***/ function(module, exports, __webpack_require__) {

/*!
 * Pikaday
 *
 * Copyright © 2014 David Bushell | BSD & MIT license | https://github.com/dbushell/Pikaday
 */

(function (root, factory)
{
    'use strict';

    var moment;
    if (true) {
        // CommonJS module
        // Load moment.js as an optional dependency
        try { moment = __webpack_require__(53); } catch (e) {}
        module.exports = factory(moment);
    } else if (typeof define === 'function' && define.amd) {
        // AMD. Register as an anonymous module.
        define(function (req)
        {
            // Load moment.js as an optional dependency
            var id = 'moment';
            try { moment = req(id); } catch (e) {}
            return factory(moment);
        });
    } else {
        root.Pikaday = factory(root.moment);
    }
}(this, function (moment)
{
    'use strict';

    /**
     * feature detection and helper functions
     */
    var hasMoment = typeof moment === 'function',

    hasEventListeners = !!window.addEventListener,

    document = window.document,

    sto = window.setTimeout,

    addEvent = function(el, e, callback, capture)
    {
        if (hasEventListeners) {
            el.addEventListener(e, callback, !!capture);
        } else {
            el.attachEvent('on' + e, callback);
        }
    },

    removeEvent = function(el, e, callback, capture)
    {
        if (hasEventListeners) {
            el.removeEventListener(e, callback, !!capture);
        } else {
            el.detachEvent('on' + e, callback);
        }
    },

    fireEvent = function(el, eventName, data)
    {
        var ev;

        if (document.createEvent) {
            ev = document.createEvent('HTMLEvents');
            ev.initEvent(eventName, true, false);
            ev = extend(ev, data);
            el.dispatchEvent(ev);
        } else if (document.createEventObject) {
            ev = document.createEventObject();
            ev = extend(ev, data);
            el.fireEvent('on' + eventName, ev);
        }
    },

    trim = function(str)
    {
        return str.trim ? str.trim() : str.replace(/^\s+|\s+$/g,'');
    },

    hasClass = function(el, cn)
    {
        return (' ' + el.className + ' ').indexOf(' ' + cn + ' ') !== -1;
    },

    addClass = function(el, cn)
    {
        if (!hasClass(el, cn)) {
            el.className = (el.className === '') ? cn : el.className + ' ' + cn;
        }
    },

    removeClass = function(el, cn)
    {
        el.className = trim((' ' + el.className + ' ').replace(' ' + cn + ' ', ' '));
    },

    isArray = function(obj)
    {
        return (/Array/).test(Object.prototype.toString.call(obj));
    },

    isDate = function(obj)
    {
        return (/Date/).test(Object.prototype.toString.call(obj)) && !isNaN(obj.getTime());
    },

    isWeekend = function(date)
    {
        var day = date.getDay();
        return day === 0 || day === 6;
    },

    isLeapYear = function(year)
    {
        // solution by Matti Virkkunen: http://stackoverflow.com/a/4881951
        return year % 4 === 0 && year % 100 !== 0 || year % 400 === 0;
    },

    getDaysInMonth = function(year, month)
    {
        return [31, isLeapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month];
    },

    setToStartOfDay = function(date)
    {
        if (isDate(date)) date.setHours(0,0,0,0);
    },

    compareDates = function(a,b)
    {
        // weak date comparison (use setToStartOfDay(date) to ensure correct result)
        return a.getTime() === b.getTime();
    },

    extend = function(to, from, overwrite)
    {
        var prop, hasProp;
        for (prop in from) {
            hasProp = to[prop] !== undefined;
            if (hasProp && typeof from[prop] === 'object' && from[prop] !== null && from[prop].nodeName === undefined) {
                if (isDate(from[prop])) {
                    if (overwrite) {
                        to[prop] = new Date(from[prop].getTime());
                    }
                }
                else if (isArray(from[prop])) {
                    if (overwrite) {
                        to[prop] = from[prop].slice(0);
                    }
                } else {
                    to[prop] = extend({}, from[prop], overwrite);
                }
            } else if (overwrite || !hasProp) {
                to[prop] = from[prop];
            }
        }
        return to;
    },

    adjustCalendar = function(calendar) {
        if (calendar.month < 0) {
            calendar.year -= Math.ceil(Math.abs(calendar.month)/12);
            calendar.month += 12;
        }
        if (calendar.month > 11) {
            calendar.year += Math.floor(Math.abs(calendar.month)/12);
            calendar.month -= 12;
        }
        return calendar;
    },

    /**
     * defaults and localisation
     */
    defaults = {

        // bind the picker to a form field
        field: null,

        // automatically show/hide the picker on `field` focus (default `true` if `field` is set)
        bound: undefined,

        // position of the datepicker, relative to the field (default to bottom & left)
        // ('bottom' & 'left' keywords are not used, 'top' & 'right' are modifier on the bottom/left position)
        position: 'bottom left',

        // automatically fit in the viewport even if it means repositioning from the position option
        reposition: true,

        // the default output format for `.toString()` and `field` value
        format: 'YYYY-MM-DD',

        // the initial date to view when first opened
        defaultDate: null,

        // make the `defaultDate` the initial selected value
        setDefaultDate: false,

        // first day of week (0: Sunday, 1: Monday etc)
        firstDay: 0,

        // the minimum/earliest date that can be selected
        minDate: null,
        // the maximum/latest date that can be selected
        maxDate: null,

        // number of years either side, or array of upper/lower range
        yearRange: 10,

        // show week numbers at head of row
        showWeekNumber: false,

        // used internally (don't config outside)
        minYear: 0,
        maxYear: 9999,
        minMonth: undefined,
        maxMonth: undefined,

        isRTL: false,

        // Additional text to append to the year in the calendar title
        yearSuffix: '',

        // Render the month after year in the calendar title
        showMonthAfterYear: false,

        // how many months are visible
        numberOfMonths: 1,

        // when numberOfMonths is used, this will help you to choose where the main calendar will be (default `left`, can be set to `right`)
        // only used for the first display or when a selected date is not visible
        mainCalendar: 'left',

        // Specify a DOM element to render the calendar in
        container: undefined,

        // internationalization
        i18n: {
            previousMonth : 'Previous Month',
            nextMonth     : 'Next Month',
            months        : ['January','February','March','April','May','June','July','August','September','October','November','December'],
            weekdays      : ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
            weekdaysShort : ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']
        },

        // callback function
        onSelect: null,
        onOpen: null,
        onClose: null,
        onDraw: null
    },


    /**
     * templating functions to abstract HTML rendering
     */
    renderDayName = function(opts, day, abbr)
    {
        day += opts.firstDay;
        while (day >= 7) {
            day -= 7;
        }
        return abbr ? opts.i18n.weekdaysShort[day] : opts.i18n.weekdays[day];
    },

    renderDay = function(d, m, y, isSelected, isToday, isDisabled, isEmpty)
    {
        if (isEmpty) {
            return '<td class="is-empty"></td>';
        }
        var arr = [];
        if (isDisabled) {
            arr.push('is-disabled');
        }
        if (isToday) {
            arr.push('is-today');
        }
        if (isSelected) {
            arr.push('is-selected');
        }
        return '<td data-day="' + d + '" class="' + arr.join(' ') + '">' +
                 '<button class="pika-button pika-day" type="button" ' +
                    'data-pika-year="' + y + '" data-pika-month="' + m + '" data-pika-day="' + d + '">' +
                        d +
                 '</button>' +
               '</td>';
    },

    renderWeek = function (d, m, y) {
        // Lifted from http://javascript.about.com/library/blweekyear.htm, lightly modified.
        var onejan = new Date(y, 0, 1),
            weekNum = Math.ceil((((new Date(y, m, d) - onejan) / 86400000) + onejan.getDay()+1)/7);
        return '<td class="pika-week">' + weekNum + '</td>';
    },

    renderRow = function(days, isRTL)
    {
        return '<tr>' + (isRTL ? days.reverse() : days).join('') + '</tr>';
    },

    renderBody = function(rows)
    {
        return '<tbody>' + rows.join('') + '</tbody>';
    },

    renderHead = function(opts)
    {
        var i, arr = [];
        if (opts.showWeekNumber) {
            arr.push('<th></th>');
        }
        for (i = 0; i < 7; i++) {
            arr.push('<th scope="col"><abbr title="' + renderDayName(opts, i) + '">' + renderDayName(opts, i, true) + '</abbr></th>');
        }
        return '<thead>' + (opts.isRTL ? arr.reverse() : arr).join('') + '</thead>';
    },

    renderTitle = function(instance, c, year, month, refYear)
    {
        var i, j, arr,
            opts = instance._o,
            isMinYear = year === opts.minYear,
            isMaxYear = year === opts.maxYear,
            html = '<div class="pika-title">',
            monthHtml,
            yearHtml,
            prev = true,
            next = true;

        for (arr = [], i = 0; i < 12; i++) {
            arr.push('<option value="' + (year === refYear ? i - c : 12 + i - c) + '"' +
                (i === month ? ' selected': '') +
                ((isMinYear && i < opts.minMonth) || (isMaxYear && i > opts.maxMonth) ? 'disabled' : '') + '>' +
                opts.i18n.months[i] + '</option>');
        }
        monthHtml = '<div class="pika-label">' + opts.i18n.months[month] + '<select class="pika-select pika-select-month">' + arr.join('') + '</select></div>';

        if (isArray(opts.yearRange)) {
            i = opts.yearRange[0];
            j = opts.yearRange[1] + 1;
        } else {
            i = year - opts.yearRange;
            j = 1 + year + opts.yearRange;
        }

        for (arr = []; i < j && i <= opts.maxYear; i++) {
            if (i >= opts.minYear) {
                arr.push('<option value="' + i + '"' + (i === year ? ' selected': '') + '>' + (i) + '</option>');
            }
        }
        yearHtml = '<div class="pika-label">' + year + opts.yearSuffix + '<select class="pika-select pika-select-year">' + arr.join('') + '</select></div>';

        if (opts.showMonthAfterYear) {
            html += yearHtml + monthHtml;
        } else {
            html += monthHtml + yearHtml;
        }

        if (isMinYear && (month === 0 || opts.minMonth >= month)) {
            prev = false;
        }

        if (isMaxYear && (month === 11 || opts.maxMonth <= month)) {
            next = false;
        }

        if (c === 0) {
            html += '<button class="pika-prev' + (prev ? '' : ' is-disabled') + '" type="button">' + opts.i18n.previousMonth + '</button>';
        }
        if (c === (instance._o.numberOfMonths - 1) ) {
            html += '<button class="pika-next' + (next ? '' : ' is-disabled') + '" type="button">' + opts.i18n.nextMonth + '</button>';
        }

        return html += '</div>';
    },

    renderTable = function(opts, data)
    {
        return '<table cellpadding="0" cellspacing="0" class="pika-table">' + renderHead(opts) + renderBody(data) + '</table>';
    },


    /**
     * Pikaday constructor
     */
    Pikaday = function(options)
    {
        var self = this,
            opts = self.config(options);

        self._onMouseDown = function(e)
        {
            if (!self._v) {
                return;
            }
            e = e || window.event;
            var target = e.target || e.srcElement;
            if (!target) {
                return;
            }

            if (!hasClass(target, 'is-disabled')) {
                if (hasClass(target, 'pika-button') && !hasClass(target, 'is-empty')) {
                    self.setDate(new Date(target.getAttribute('data-pika-year'), target.getAttribute('data-pika-month'), target.getAttribute('data-pika-day')));
                    if (opts.bound) {
                        sto(function() {
                            self.hide();
                            if (opts.field) {
                                opts.field.blur();
                            }
                        }, 100);
                    }
                    return;
                }
                else if (hasClass(target, 'pika-prev')) {
                    self.prevMonth();
                }
                else if (hasClass(target, 'pika-next')) {
                    self.nextMonth();
                }
            }
            if (!hasClass(target, 'pika-select')) {
                if (e.preventDefault) {
                    e.preventDefault();
                } else {
                    e.returnValue = false;
                    return false;
                }
            } else {
                self._c = true;
            }
        };

        self._onChange = function(e)
        {
            e = e || window.event;
            var target = e.target || e.srcElement;
            if (!target) {
                return;
            }
            if (hasClass(target, 'pika-select-month')) {
                self.gotoMonth(target.value);
            }
            else if (hasClass(target, 'pika-select-year')) {
                self.gotoYear(target.value);
            }
        };

        self._onInputChange = function(e)
        {
            var date;

            if (e.firedBy === self) {
                return;
            }
            if (hasMoment) {
                date = moment(opts.field.value, opts.format);
                date = (date && date.isValid()) ? date.toDate() : null;
            }
            else {
                date = new Date(Date.parse(opts.field.value));
            }
            self.setDate(isDate(date) ? date : null);
            if (!self._v) {
                self.show();
            }
        };

        self._onInputFocus = function()
        {
            self.show();
        };

        self._onInputClick = function()
        {
            self.show();
        };

        self._onInputBlur = function()
        {
            // IE allows pika div to gain focus; catch blur the input field
            var pEl = document.activeElement;
            do {
                if (hasClass(pEl, 'pika-single')) {
                    return;
                }
            }
            while ((pEl = pEl.parentNode));
            
            if (!self._c) {
                self._b = sto(function() {
                    self.hide();
                }, 50);
            }
            self._c = false;
        };

        self._onClick = function(e)
        {
            e = e || window.event;
            var target = e.target || e.srcElement,
                pEl = target;
            if (!target) {
                return;
            }
            if (!hasEventListeners && hasClass(target, 'pika-select')) {
                if (!target.onchange) {
                    target.setAttribute('onchange', 'return;');
                    addEvent(target, 'change', self._onChange);
                }
            }
            do {
                if (hasClass(pEl, 'pika-single') || pEl === opts.trigger) {
                    return;
                }
            }
            while ((pEl = pEl.parentNode));
            if (self._v && target !== opts.trigger && pEl !== opts.trigger) {
                self.hide();
            }
        };

        self.el = document.createElement('div');
        self.el.className = 'pika-single' + (opts.isRTL ? ' is-rtl' : '');

        addEvent(self.el, 'mousedown', self._onMouseDown, true);
        addEvent(self.el, 'change', self._onChange);

        if (opts.field) {
            if (opts.container) {
                opts.container.appendChild(self.el);
            } else if (opts.bound) {
                document.body.appendChild(self.el);
            } else {
                opts.field.parentNode.insertBefore(self.el, opts.field.nextSibling);
            }
            addEvent(opts.field, 'change', self._onInputChange);

            if (!opts.defaultDate) {
                if (hasMoment && opts.field.value) {
                    opts.defaultDate = moment(opts.field.value, opts.format).toDate();
                } else {
                    opts.defaultDate = new Date(Date.parse(opts.field.value));
                }
                opts.setDefaultDate = true;
            }
        }

        var defDate = opts.defaultDate;

        if (isDate(defDate)) {
            if (opts.setDefaultDate) {
                self.setDate(defDate, true);
            } else {
                self.gotoDate(defDate);
            }
        } else {
            self.gotoDate(new Date());
        }

        if (opts.bound) {
            this.hide();
            self.el.className += ' is-bound';
            addEvent(opts.trigger, 'click', self._onInputClick);
            addEvent(opts.trigger, 'focus', self._onInputFocus);
            addEvent(opts.trigger, 'blur', self._onInputBlur);
        } else {
            this.show();
        }
    };


    /**
     * public Pikaday API
     */
    Pikaday.prototype = {


        /**
         * configure functionality
         */
        config: function(options)
        {
            if (!this._o) {
                this._o = extend({}, defaults, true);
            }

            var opts = extend(this._o, options, true);

            opts.isRTL = !!opts.isRTL;

            opts.field = (opts.field && opts.field.nodeName) ? opts.field : null;

            opts.bound = !!(opts.bound !== undefined ? opts.field && opts.bound : opts.field);

            opts.trigger = (opts.trigger && opts.trigger.nodeName) ? opts.trigger : opts.field;

            opts.disableWeekends = !!opts.disableWeekends;

            opts.disableDayFn = (typeof opts.disableDayFn) == "function" ? opts.disableDayFn : null;

            var nom = parseInt(opts.numberOfMonths, 10) || 1;
            opts.numberOfMonths = nom > 4 ? 4 : nom;

            if (!isDate(opts.minDate)) {
                opts.minDate = false;
            }
            if (!isDate(opts.maxDate)) {
                opts.maxDate = false;
            }
            if ((opts.minDate && opts.maxDate) && opts.maxDate < opts.minDate) {
                opts.maxDate = opts.minDate = false;
            }
            if (opts.minDate) {
                setToStartOfDay(opts.minDate);
                opts.minYear  = opts.minDate.getFullYear();
                opts.minMonth = opts.minDate.getMonth();
            }
            if (opts.maxDate) {
                setToStartOfDay(opts.maxDate);
                opts.maxYear  = opts.maxDate.getFullYear();
                opts.maxMonth = opts.maxDate.getMonth();
            }

            if (isArray(opts.yearRange)) {
                var fallback = new Date().getFullYear() - 10;
                opts.yearRange[0] = parseInt(opts.yearRange[0], 10) || fallback;
                opts.yearRange[1] = parseInt(opts.yearRange[1], 10) || fallback;
            } else {
                opts.yearRange = Math.abs(parseInt(opts.yearRange, 10)) || defaults.yearRange;
                if (opts.yearRange > 100) {
                    opts.yearRange = 100;
                }
            }

            return opts;
        },

        /**
         * return a formatted string of the current selection (using Moment.js if available)
         */
        toString: function(format)
        {
            return !isDate(this._d) ? '' : hasMoment ? moment(this._d).format(format || this._o.format) : this._d.toDateString();
        },

        /**
         * return a Moment.js object of the current selection (if available)
         */
        getMoment: function()
        {
            return hasMoment ? moment(this._d) : null;
        },

        /**
         * set the current selection from a Moment.js object (if available)
         */
        setMoment: function(date, preventOnSelect)
        {
            if (hasMoment && moment.isMoment(date)) {
                this.setDate(date.toDate(), preventOnSelect);
            }
        },

        /**
         * return a Date object of the current selection
         */
        getDate: function()
        {
            return isDate(this._d) ? new Date(this._d.getTime()) : null;
        },

        /**
         * set the current selection
         */
        setDate: function(date, preventOnSelect)
        {
            if (!date) {
                this._d = null;

                if (this._o.field) {
                    this._o.field.value = '';
                    fireEvent(this._o.field, 'change', { firedBy: this });
                }

                return this.draw();
            }
            if (typeof date === 'string') {
                date = new Date(Date.parse(date));
            }
            if (!isDate(date)) {
                return;
            }

            var min = this._o.minDate,
                max = this._o.maxDate;

            if (isDate(min) && date < min) {
                date = min;
            } else if (isDate(max) && date > max) {
                date = max;
            }

            this._d = new Date(date.getTime());
            setToStartOfDay(this._d);
            this.gotoDate(this._d);

            if (this._o.field) {
                this._o.field.value = this.toString();
                fireEvent(this._o.field, 'change', { firedBy: this });
            }
            if (!preventOnSelect && typeof this._o.onSelect === 'function') {
                this._o.onSelect.call(this, this.getDate());
            }
        },

        /**
         * change view to a specific date
         */
        gotoDate: function(date)
        {
            var newCalendar = true;

            if (!isDate(date)) {
                return;
            }

            if (this.calendars) {
                var firstVisibleDate = new Date(this.calendars[0].year, this.calendars[0].month, 1),
                    lastVisibleDate = new Date(this.calendars[this.calendars.length-1].year, this.calendars[this.calendars.length-1].month, 1),
                    visibleDate = date.getTime();
                // get the end of the month
                lastVisibleDate.setMonth(lastVisibleDate.getMonth()+1);
                lastVisibleDate.setDate(lastVisibleDate.getDate()-1);
                newCalendar = (visibleDate < firstVisibleDate.getTime() || lastVisibleDate.getTime() < visibleDate);
            }

            if (newCalendar) {
                this.calendars = [{
                    month: date.getMonth(),
                    year: date.getFullYear()
                }];
                if (this._o.mainCalendar === 'right') {
                    this.calendars[0].month += 1 - this._o.numberOfMonths;
                }
            }

            this.adjustCalendars();
        },

        adjustCalendars: function() {
            this.calendars[0] = adjustCalendar(this.calendars[0]);
            for (var c = 1; c < this._o.numberOfMonths; c++) {
                this.calendars[c] = adjustCalendar({
                    month: this.calendars[0].month + c,
                    year: this.calendars[0].year
                });
            }
            this.draw();
        },

        gotoToday: function()
        {
            this.gotoDate(new Date());
        },

        /**
         * change view to a specific month (zero-index, e.g. 0: January)
         */
        gotoMonth: function(month)
        {
            if (!isNaN(month)) {
                this.calendars[0].month = parseInt(month, 10);
                this.adjustCalendars();
            }
        },

        nextMonth: function()
        {
            this.calendars[0].month++;
            this.adjustCalendars();
        },

        prevMonth: function()
        {
            this.calendars[0].month--;
            this.adjustCalendars();
        },

        /**
         * change view to a specific full year (e.g. "2012")
         */
        gotoYear: function(year)
        {
            if (!isNaN(year)) {
                this.calendars[0].year = parseInt(year, 10);
                this.adjustCalendars();
            }
        },

        /**
         * change the minDate
         */
        setMinDate: function(value)
        {
            this._o.minDate = value;
        },

        /**
         * change the maxDate
         */
        setMaxDate: function(value)
        {
            this._o.maxDate = value;
        },

        /**
         * refresh the HTML
         */
        draw: function(force)
        {
            if (!this._v && !force) {
                return;
            }
            var opts = this._o,
                minYear = opts.minYear,
                maxYear = opts.maxYear,
                minMonth = opts.minMonth,
                maxMonth = opts.maxMonth,
                html = '';

            if (this._y <= minYear) {
                this._y = minYear;
                if (!isNaN(minMonth) && this._m < minMonth) {
                    this._m = minMonth;
                }
            }
            if (this._y >= maxYear) {
                this._y = maxYear;
                if (!isNaN(maxMonth) && this._m > maxMonth) {
                    this._m = maxMonth;
                }
            }

            for (var c = 0; c < opts.numberOfMonths; c++) {
                html += '<div class="pika-lendar">' + renderTitle(this, c, this.calendars[c].year, this.calendars[c].month, this.calendars[0].year) + this.render(this.calendars[c].year, this.calendars[c].month) + '</div>';
            }

            this.el.innerHTML = html;

            if (opts.bound) {
                if(opts.field.type !== 'hidden') {
                    sto(function() {
                        opts.trigger.focus();
                    }, 1);
                }
            }

            if (typeof this._o.onDraw === 'function') {
                var self = this;
                sto(function() {
                    self._o.onDraw.call(self);
                }, 0);
            }
        },

        adjustPosition: function()
        {
            if (this._o.container) return;
            var field = this._o.trigger, pEl = field,
            width = this.el.offsetWidth, height = this.el.offsetHeight,
            viewportWidth = window.innerWidth || document.documentElement.clientWidth,
            viewportHeight = window.innerHeight || document.documentElement.clientHeight,
            scrollTop = window.pageYOffset || document.body.scrollTop || document.documentElement.scrollTop,
            left, top, clientRect;

            if (typeof field.getBoundingClientRect === 'function') {
                clientRect = field.getBoundingClientRect();
                left = clientRect.left + window.pageXOffset;
                top = clientRect.bottom + window.pageYOffset;
            } else {
                left = pEl.offsetLeft;
                top  = pEl.offsetTop + pEl.offsetHeight;
                while((pEl = pEl.offsetParent)) {
                    left += pEl.offsetLeft;
                    top  += pEl.offsetTop;
                }
            }

            // default position is bottom & left
            if ((this._o.reposition && left + width > viewportWidth) ||
                (
                    this._o.position.indexOf('right') > -1 &&
                    left - width + field.offsetWidth > 0
                )
            ) {
                left = left - width + field.offsetWidth;
            }
            if ((this._o.reposition && top + height > viewportHeight + scrollTop) ||
                (
                    this._o.position.indexOf('top') > -1 &&
                    top - height - field.offsetHeight > 0
                )
            ) {
                top = top - height - field.offsetHeight;
            }

            this.el.style.cssText = [
                'position: absolute',
                'left: ' + left + 'px',
                'top: ' + top + 'px'
            ].join(';');
        },

        /**
         * render HTML for a particular month
         */
        render: function(year, month)
        {
            var opts   = this._o,
                now    = new Date(),
                days   = getDaysInMonth(year, month),
                before = new Date(year, month, 1).getDay(),
                data   = [],
                row    = [];
            setToStartOfDay(now);
            if (opts.firstDay > 0) {
                before -= opts.firstDay;
                if (before < 0) {
                    before += 7;
                }
            }
            var cells = days + before,
                after = cells;
            while(after > 7) {
                after -= 7;
            }
            cells += 7 - after;
            for (var i = 0, r = 0; i < cells; i++)
            {
                var day = new Date(year, month, 1 + (i - before)),
                    isSelected = isDate(this._d) ? compareDates(day, this._d) : false,
                    isToday = compareDates(day, now),
                    isEmpty = i < before || i >= (days + before),
                    isDisabled = (opts.minDate && day < opts.minDate) ||
                                 (opts.maxDate && day > opts.maxDate) ||
                                 (opts.disableWeekends && isWeekend(day)) ||
                                 (opts.disableDayFn && opts.disableDayFn(day));

                row.push(renderDay(1 + (i - before), month, year, isSelected, isToday, isDisabled, isEmpty));

                if (++r === 7) {
                    if (opts.showWeekNumber) {
                        row.unshift(renderWeek(i - before, month, year));
                    }
                    data.push(renderRow(row, opts.isRTL));
                    row = [];
                    r = 0;
                }
            }
            return renderTable(opts, data);
        },

        isVisible: function()
        {
            return this._v;
        },

        show: function()
        {
            if (!this._v) {
                removeClass(this.el, 'is-hidden');
                this._v = true;
                this.draw();
                if (this._o.bound) {
                    addEvent(document, 'click', this._onClick);
                    this.adjustPosition();
                }
                if (typeof this._o.onOpen === 'function') {
                    this._o.onOpen.call(this);
                }
            }
        },

        hide: function()
        {
            var v = this._v;
            if (v !== false) {
                if (this._o.bound) {
                    removeEvent(document, 'click', this._onClick);
                }
                this.el.style.cssText = '';
                addClass(this.el, 'is-hidden');
                this._v = false;
                if (v !== undefined && typeof this._o.onClose === 'function') {
                    this._o.onClose.call(this);
                }
            }
        },

        /**
         * GAME OVER
         */
        destroy: function()
        {
            this.hide();
            removeEvent(this.el, 'mousedown', this._onMouseDown, true);
            removeEvent(this.el, 'change', this._onChange);
            if (this._o.field) {
                removeEvent(this._o.field, 'change', this._onInputChange);
                if (this._o.bound) {
                    removeEvent(this._o.trigger, 'click', this._onInputClick);
                    removeEvent(this._o.trigger, 'focus', this._onInputFocus);
                    removeEvent(this._o.trigger, 'blur', this._onInputBlur);
                }
            }
            if (this.el.parentNode) {
                this.el.parentNode.removeChild(this.el);
            }
        }

    };

    return Pikaday;

}));


/***/ },

/***/ 412:
/***/ function(module, exports, __webpack_require__) {

// style-loader: Adds some css to the DOM by adding a <style> tag

// load the styles
var content = __webpack_require__(413);
if(typeof content === 'string') content = [[module.id, content, '']];
// add the styles to the DOM
var update = __webpack_require__(19)(content, {});
// Hot Module Replacement
if(false) {
	// When the styles change, update the <style> tags
	module.hot.accept("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/node_modules/pikaday/css/pikaday.css", function() {
		var newContent = require("!!/Users/laurenbarker/GitHub/osf.io/node_modules/css-loader/index.js!/Users/laurenbarker/GitHub/osf.io/node_modules/pikaday/css/pikaday.css");
		if(typeof newContent === 'string') newContent = [[module.id, newContent, '']];
		update(newContent);
	});
	// When the module is disposed, remove the <style> tags
	module.hot.dispose(function() { update(); });
}

/***/ },

/***/ 413:
/***/ function(module, exports, __webpack_require__) {

exports = module.exports = __webpack_require__(16)();
exports.push([module.id, "@charset \"UTF-8\";\n\n/*!\n * Pikaday\n * Copyright © 2014 David Bushell | BSD & MIT license | http://dbushell.com/\n */\n\n.pika-single {\n    z-index: 9999;\n    display: block;\n    position: relative;\n    color: #333;\n    background: #fff;\n    border: 1px solid #ccc;\n    border-bottom-color: #bbb;\n    font-family: \"Helvetica Neue\", Helvetica, Arial, sans-serif;\n}\n\n/*\nclear child float (pika-lendar), using the famous micro clearfix hack\nhttp://nicolasgallagher.com/micro-clearfix-hack/\n*/\n.pika-single:before,\n.pika-single:after {\n    content: \" \";\n    display: table;\n}\n.pika-single:after { clear: both }\n.pika-single { *zoom: 1 }\n\n.pika-single.is-hidden {\n    display: none;\n}\n\n.pika-single.is-bound {\n    position: absolute;\n    box-shadow: 0 5px 15px -5px rgba(0,0,0,.5);\n}\n\n.pika-lendar {\n    float: left;\n    width: 240px;\n    margin: 8px;\n}\n\n.pika-title {\n    position: relative;\n    text-align: center;\n}\n\n.pika-label {\n    display: inline-block;\n    *display: inline;\n    position: relative;\n    z-index: 9999;\n    overflow: hidden;\n    margin: 0;\n    padding: 5px 3px;\n    font-size: 14px;\n    line-height: 20px;\n    font-weight: bold;\n    background-color: #fff;\n}\n.pika-title select {\n    cursor: pointer;\n    position: absolute;\n    z-index: 9998;\n    margin: 0;\n    left: 0;\n    top: 5px;\n    filter: alpha(opacity=0);\n    opacity: 0;\n}\n\n.pika-prev,\n.pika-next {\n    display: block;\n    cursor: pointer;\n    position: relative;\n    outline: none;\n    border: 0;\n    padding: 0;\n    width: 20px;\n    height: 30px;\n    /* hide text using text-indent trick, using width value (it's enough) */\n    text-indent: 20px;\n    white-space: nowrap;\n    overflow: hidden;\n    background-color: transparent;\n    background-position: center center;\n    background-repeat: no-repeat;\n    background-size: 75% 75%;\n    opacity: .5;\n    *position: absolute;\n    *top: 0;\n}\n\n.pika-prev:hover,\n.pika-next:hover {\n    opacity: 1;\n}\n\n.pika-prev,\n.is-rtl .pika-next {\n    float: left;\n    background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAeCAYAAAAsEj5rAAAAUklEQVR42u3VMQoAIBADQf8Pgj+OD9hG2CtONJB2ymQkKe0HbwAP0xucDiQWARITIDEBEnMgMQ8S8+AqBIl6kKgHiXqQqAeJepBo/z38J/U0uAHlaBkBl9I4GwAAAABJRU5ErkJggg==');\n    *left: 0;\n}\n\n.pika-next,\n.is-rtl .pika-prev {\n    float: right;\n    background-image: url('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAeCAYAAAAsEj5rAAAAU0lEQVR42u3VOwoAMAgE0dwfAnNjU26bYkBCFGwfiL9VVWoO+BJ4Gf3gtsEKKoFBNTCoCAYVwaAiGNQGMUHMkjGbgjk2mIONuXo0nC8XnCf1JXgArVIZAQh5TKYAAAAASUVORK5CYII=');\n    *right: 0;\n}\n\n.pika-prev.is-disabled,\n.pika-next.is-disabled {\n    cursor: default;\n    opacity: .2;\n}\n\n.pika-select {\n    display: inline-block;\n    *display: inline;\n}\n\n.pika-table {\n    width: 100%;\n    border-collapse: collapse;\n    border-spacing: 0;\n    border: 0;\n}\n\n.pika-table th,\n.pika-table td {\n    width: 14.285714285714286%;\n    padding: 0;\n}\n\n.pika-table th {\n    color: #999;\n    font-size: 12px;\n    line-height: 25px;\n    font-weight: bold;\n    text-align: center;\n}\n\n.pika-button {\n    cursor: pointer;\n    display: block;\n    box-sizing: border-box;\n    -moz-box-sizing: border-box;\n    outline: none;\n    border: 0;\n    margin: 0;\n    width: 100%;\n    padding: 5px;\n    color: #666;\n    font-size: 12px;\n    line-height: 15px;\n    text-align: right;\n    background: #f5f5f5;\n}\n\n.pika-week {\n    font-size: 11px;\n    color: #999;\n}\n\n.is-today .pika-button {\n    color: #33aaff;\n    font-weight: bold;\n}\n\n.is-selected .pika-button {\n    color: #fff;\n    font-weight: bold;\n    background: #33aaff;\n    box-shadow: inset 0 1px 3px #178fe5;\n    border-radius: 3px;\n}\n\n.is-disabled .pika-button {\n    pointer-events: none;\n    cursor: default;\n    color: #999;\n    opacity: .3;\n}\n\n.pika-button:hover {\n    color: #fff !important;\n    background: #ff8000 !important;\n    box-shadow: none !important;\n    border-radius: 3px !important;\n}\n\n/* styling for abbr */\n.pika-table abbr {\n    border-bottom: none;\n    cursor: help;\n}\n\n", ""]);

/***/ }

});
//# sourceMappingURL=register_1-page.js.map