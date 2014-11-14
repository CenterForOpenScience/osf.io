/**
 * Knockout models for controlling meta-data; bound to HTML in
 * website/templates/metadata/metadata_*.mako
 */
var ko = require('knockout');

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
                        });
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
                } else if (this.type == 'section' || !child.repeatSection) {
                    idx.unshift(ko.utils.unwrapObservable(child.id));
                }
                if (child.$parent && child.$parent.observedData) {
                    key = idx.join(SEPARATOR);
                    if (action == 'add') {
                        child.$parent['observedData'][key] = this;
                    } else if (action == 'remove') {
                        delete child.$parent['observedData'][key];
                    }
                }
                child = child.$parent;
            }

            key = idx.join(SEPARATOR);
            if (action == 'add') {
                this.$root['observedData'][key] = this;
            } else if (action == 'remove') {
                delete this.$root['observedData'][key];
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

        if (self.repeatType == 'repeat') {
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

        if ('options' in self && typeof(self.options) == 'string') {
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
                        if (option['value']) {
                            return option['value']();
                        }
                        return option;
                    });
                }
                return [];
            });
        }

        // Set up observable on value
        if (self.multiple || self.type == 'checkbox') {
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
            return this.value() == value;
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
                )
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
            if (value[0] && this.$root.nodes.indexOf(value[0]) == -1) {
                this.$root.nodes.unshift(value[0]);
            }
            this.node(value[0]);
            this.value(value[1]);
            return this.node() == value[0] && this.value() == value[1];
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
        return new (Function.prototype.bind.apply(klass, args));
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
            if (content.id.indexOf(char) != -1) {
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
            return data['type'] == 'section' ? 'section' : 'item';
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
                scrollTop: $("#meta-data-container").offset().top
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
                        if (current && current.repeatType == 'repeat') {
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
                if (Object.keys(nextData).length == Object.keys(data).length) {
                    throw "Unserialize failed";
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
