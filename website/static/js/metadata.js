var MetaData = (function() {

    var SEPARATOR = '-';
    var IDX_SEPARATOR = ':';
    var TPL_REGEX = /{{(.*?)}}/;

    ko.bindingHandlers.item = {
        init: function(element, valueAccessor, allBindingsAccessor, viewModel, bindingContext) {
            var model = ko.utils.unwrapObservable(valueAccessor());
            ko.renderTemplate(model.type, model, {}, element, 'replaceNode');
        }
    };

    // Initialize unique index for Content objects
    var contentIdx = 0;

//    function Content(content, $parent, $root, $ctx, refresh) {
//        var self = this;
//        self.$parent = $parent;
//        self.$root = $root;
//        self.$ctx = $ctx;
//    }
//
//    function Section() {
//        var self = this;
//        Content.apply(this, arguments);
//
//        var tmpContents = self.contents;
//        self.contents = ko.observableArray();
//        self._contentDict = {};
//        $.each(tmpContents, function(idx, content) {
//            var newContent = new Content(content, self, $root, null, false);
//            self.contents.push(newContent);
//            self._contentDict[content.id] = newContent;
//        });
//
//    }
//    Section.prototype = new Content;
//
//    function Item() {
//        Content.apply(this, arguments);
//    }
//    Item.prototype = new Content;
//    $.extend(Item.prototype, {
//        serialize: function() {
//            return this.value();
//        },
//        unserialize: function(value) {
//            this.value(value);
//            return this.value() == value;
//        }
//    });
//
//    function FileItem() {
//        Item.apply(this, arguments);
//    }
//    FileItem.prototype = new Item;
//    $.extend(FileItem.prototype, {
//        serialize: function() {
//            return [this.node(), this.value()];
//        },
//        unserialize: function(value) {
//            this.node(value[0]);
//            this.value(value[1]);
//            return this.node() == value[0] && this.value() == value[1];
//        }
//    });

    function Content(content, $parent, $root, $ctx, refresh) {

        var self = this;

        self.$parent = $parent;
        self.$root = $root;
        self.$ctx = $ctx;

        // Give each Content a unique index for tracking
        self.contentIdx = contentIdx;
        contentIdx++;

        $.extend(self, content);

        if ('contents' in self) {
            var tmpContents = self.contents;
            self.contents = ko.observableArray();
            $.each(tmpContents, function(idx, content) {
                var newContent = new Content(content, self, $root, null, false);
                self.contents.push(newContent);
            });
        }

        if (self.repeatType == 'repeat') {
            self.initRepeat = self.initRepeat || 1;
            for (var i=0; i<self.initRepeat; i++) {
                self.addRepeat(null, false);
            }
        }

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

        if ('each' in self && content.repeatType == 'each') {
            if (typeof(self.each) == 'string') {
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
                            var key = data.contentIdx;
                            if (!(key in self._contentsData)) {
                                var newContent = new Content(self._template, self, self.$root, data, false);
                                newContent.updateIdx('add', false);
                                self._contentsData[key] = newContent;
                            }
                            return self._contentsData[key];
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
        self.validation = self.validation || [];
        self.canRepeat = self.canRepeat || false;
        self.minRepeat = typeof(self.minRepeat) != 'undefined' ? self.minRepeat : 1;
        self.maxRepeat = self.maxRepeat || null;

        $.each(['id', 'title', 'label', 'caption', 'value'], function(idx, field) {
            // todo: recurse over iterables
            if (self[field] && typeof(self[field]) == 'string' && self[field].match(TPL_REGEX)) {
                self.contextComputed(field);
            }
        });

        if (self.type != 'section') {

            self.idx = null;
            self.prevIdx = null;

            // Set up observable on value
            if (self.multiple || self.type == 'checkbox') {
                self.value = ko.observableArray(self.value || []);
            } else {
                self.value = ko.observable(ko.utils.unwrapObservable(self.value) || '');
            }
            // Impute question-level defaults
            self.required = self.required || false;
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

            // todo: move into separate class
            if (self.type == 'file') {
                self.node = ko.observable();
                self.serialize = function() {
                    return [self.node(), self.value()];
                };
                self.unserialize = function(data) {
                    // Ensure that stored node is included in view model's
                    // node list
                    if (data[0] && self.$root.nodes.indexOf(data[0]) == -1) {
                        self.$root.nodes.unshift(data[0]);
                    }
                    self.node(data[0]);
                    self.value(data[1]);
                    return true;
                };
                self.nodes = self.$root.nodes;
                self.files = ko.computed(function() {
                    var selectedNode = self.node();
                    console.log(self.id + ' selected ' + selectedNode);
                    if (!selectedNode) {
                        return [];
                    }
                    if (!self.$root.fileDict[selectedNode]) {
                        self.$root.fileDict[selectedNode] = ko.observableArray();
                        self.$root.fileDict[selectedNode]();
                        $.getJSON(
                            nodeToUseUrl() + 'file_paths/',
                            function(response) {
                                self.$root.fileDict[selectedNode](response.files);
                            }
                        )
                    } else {
                        return self.$root.fileDict[selectedNode]();
                    }
                });
            }

        } else {

            self.observedData = {};

        }

        self.visible = ko.computed(function() {
            self.$root._refresh();
            var _visible = true;
            $.each(self.displayRules, function(key, value) {
                var model = self.getKey(key);
                var modelValue = model ? model.value() : null;
                if (modelValue != value) {
                    _visible = false;
                    return false;
                }
            });
            return _visible;
        });

        if (refresh) {
            $root.refresh();
        }

    }

    Content.prototype = {

        contextComputed: function(field) {
            var self = this;
            var _original = self[field];
            self[field] = ko.computed(function() {
                value = _original;
                while (match = value.match(TPL_REGEX)) {
                    ctxSplit = match[1].split('.');
                    if (ctxSplit[0] == '$ctx') {
                        cntValue = self;
                        ctxValue = self.$ctx;
                        $.each(ctxSplit.slice(1), function(idx, key) {
                            if (key == '$parent') {
                                cntValue = cntValue.$parent;
                                ctxValue = cntValue.$ctx;
                            } else {
                                ctxValue = ctxValue[key];
                            }
                        });
                    } else if (ctxSplit[0] == '$svy') {
                        model = self.getKey(ctxSplit[1]);
                        ctxValue = model ? model.value() : '';
                    }
                    value = value.replace(TPL_REGEX, ko.utils.unwrapObservable(ctxValue));
                }
                return value;
            });
        },

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
//                    } else {
//            if (this.type != 'section' || this.repeatSection) {
            if (true) {
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
                    //else {
//                                idx.unshift(child.id);
//                            }
                    if (child.$parent && child.$parent.observedData) {
//                                if (idx.length) {
////                                    key = this.id + '-' + idx.join('-');
//                                    key = idx.join('-');
//                                } else {
//                                    key = this.id;
//                                }
                        key = idx.join(SEPARATOR);
                        if (action == 'add') {
                            child.$parent['observedData'][key] = this;
                        } else if (action == 'remove') {
                            delete child.$parent['observedData'][key];
                        }
                    }
                    child = child.$parent;
                }
//                        key = idx.length ? this.id + '-' + idx.join('-') :
//                                this.id;
                key = idx.join(SEPARATOR);
                if (action == 'add') {
                    this.$root['observedData'][key] = this;
                } else if (action == 'remove') {
                    delete this.$root['observedData'][key];
                }
            }

            if (refresh) {
                console.log('calling refresh');
                console.log(refresh);
                this.$root.refresh();
            }

        },

        addRepeat: function(data, update) {
            var content = new Content(this._template, this, this.$root, data);
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

    function Page(id, title, contents, $root) {

        var self = this;

        self.id = id;
        self.title = title;
        self.contents = ko.observableArray();
        $.each(contents, function(idx, content) {
            var newContent = new Content(content, self, $root);
            self.contents.push(newContent);
        });

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

            if (_content.canRepeat) {
                content.contents[idx] = {
                    type: 'section',
                    title: null,
                    id: _content.id,
                    minRepeat: _content.minRepeat,
                    maxRepeat: _content.maxRepeat,
                    initRepeat: _content.initRepeat,
                    repeatType: 'repeat',
                    repeatSection: true,
                    contents: [],
                    _template: _content
                };
            } else if (_content.each) {
                content.contents[idx] = {
                    type: 'section',
                    each: _content.each,
                    title: null,
                    id: _content.id,
                    repeatType: 'each',
                    repeatSection: true,
                    contents: [],
                    _template: _content
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
            return self.continueText() === 'continue';
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
            if (data.$parent.repeatType != 'repeat' || data.disable || this.disable) {
                return false;
            }
            var count = data.$parent.repeatCount ? data.$parent.repeatCount() : null;
            return data.$parent.repeatSection &&
                    count > data.minRepeat;
        },

        canAdd: function(data) {
            if (data.repeatType != 'repeat' || data.disable || this.disable) {
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
            var data = {},
                complete = true,
                value;
            $.each(this.observedData, function(name, model) {
                if (model.serialize) {
                    data[name] = model.serialize();
                } else {
                    // Skip if not item
                    if (!model.value) {
                        return true;
                    }
                    value = model.value();
                    if (model.visible())
                        data[name] = model.value();
                    if (complete && model.required && !value)
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
                console.log('unserializing ' + key + ' ' + value);
                var keyParts = key.split(SEPARATOR);
                var current = self;
                var subIdx;
                $.each(keyParts, function(idx, keyPart) {
                    subParts = keyPart.split(IDX_SEPARATOR);
                    console.log(subParts[0]);
                    current = current.observedData[subParts[0]];
                    if (subParts.length > 1) {
                        if (current && current.repeatType == 'repeat') {
                            subIdx = parseInt(subParts[1]);
                            while (current.contents().length < (subIdx + 1)) {
                                current.addRepeat(null, true);
                            }
                            console.log('contents');
                            console.log(current.contents());
                            current = current.contents()[subIdx];
                        }
                    }
                });
                if (self.observedData[key]) {
                    if (self.observedData[key].unserialize) {
                        var success = self.observedData[key].unserialize(value);
                        if (!success) {
                            nextData[key] = value;
                        }
                    } else {
                        self.observedData[key].value(value);
                        if (self.observedData[key].value() != value) {
                            nextData[key] = value;
                        }
                    }
                } else {
                    nextData[key] = value;
                }
            });
            console.log('nextData ' + nextData);
            if (Object.keys(nextData).length) {
                // Length of data to be unserialized hasn't changed;
                // we're stuck!
                if (Object.keys(nextData).length == Object.keys(data).length) {
                    console.log(nextData);
                    throw "Unserialize failed";
                }
                // Unserialize remaining data
                self.unserialize(nextData);
            }
        },

        submit: function() {
            var serialized = this.serialize();
            if (!serialized['complete']) {
                console.log('Survey not complete!');
            } else {
                console.log('Submitting data: ' + JSON.stringify(serialized['data']));
            }
        }

    };

    return {
        ViewModel: ViewModel,
        Content: Content
    }

}());