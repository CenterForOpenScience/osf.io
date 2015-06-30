var jedit = require('json-editor'); //TODO webpackify
var FilesWidget = require('js/FilesWidget');
var Fangorn = require('js/fangorn');
var $osf = require('js/osfHelpers');
var $ = require('jquery');
var URI = require('URIjs');

require('json-editor');

var curentUser = window.contextVars.currentUser || {
    pk: null,
    name: 'Anonymous'
};

/////////////////// description placement //////////
JSONEditor.defaults.themes.bootstrap3_OSF = JSONEditor.defaults.themes.bootstrap3.extend({
    getFormControl: function(label, input, description, help) {
        var group = document.createElement("div");

        if (label && input.type === "checkbox") {
            group.className += " checkbox";
            label.appendChild(input);
            label.style.fontSize = "14px";
            group.style.marginTop = "0";
            group.appendChild(label);
            input.style.position = "relative";
            input.style.cssFloat = "left";
        } else {
            group.className += " form-group";
            if (label) {
                label.className += " control-label";
                group.appendChild(label);
            }
            if (description) {
                group.appendChild(description);
            }
            if (help) {
                group.appendChild(help);
            }
            group.appendChild(input);
        }

        return group;
    },
    getFormInputHelp: function(text) {
        var el = document.createElement('p');
        el.className = 'example-block';
        el.innerHTML = '<a>Show Example</a>';
        var el_inner = document.createElement('p');
        el_inner.id = 'example';
        el_inner.innerHTML = text;
        el.appendChild(el_inner);
        return el;
    },
});

//######### Commentable ###########

var Comments = function($element) {

    var self = this;

    self.comments = [];
    self.lastModified = '';

    var $commentsDiv = $('<div>');
    var $commentsList = $('<ul>', {
        'class': 'list-group'
    });
    self.$commentsList = $commentsList;
    $commentsDiv.append($commentsList);
    $commentsDiv.append($('<button>', {
        'class': 'btn btn-success',
        html: 'Add comment',
        click: self.add.bind(self)
    }));
    $element.append($commentsDiv);

    self.add();
};
Comments.prototype.Comment = function(value) {
    var self = this;

    value = value || '';

    self.user = {
        pk: curentUser.id,
        name: curentUser.fullname
    };

    self.editable = true;

    self.$input = $('<input>', {
        'class': 'form-control',
        type: 'text',
        placeholder: 'Leave a comment for a reviewer',
        html: value
    });
    self.$label = $('<span>', {
        html: function() {
            if (window.contextVars.currentUser.id === self.user.pk) {
                return '<strong>You</strong> said...';
            }
            return '<strong>' + self.user.fullname + '</strong> said...';
        }
    });
    self.$element = $('<li>', {
        'class': 'list-group-item'
    });
    var $row = $('<div>', {
        'class': 'row'
    });
    $row.append($('<div>', {
        'class': 'col-md-12'
    }).append(self.$input));

    var $control = $('<span>');
    self.$saveComment = $('<a>', {
        'class': 'btn fa fa-save',
        click: function() {
            if (window.contextVars.currentUser.id === self.user.pk) {
                if (self.$input.value !== '') {
                    self.$element.last().before(self.$label);
                }

                self.editable = false;
                self.lastModified = Date();
                $(this).addClass('disabled');
                self.$input.addClass('disabled');
                self.$editComment.removeClass('disabled');
            } else {
                throw 'Only the author may edit this comment';
            }
        }
    });
    self.$editComment = $('<a>', {
        'class': 'btn fa fa-pencil',
        click: function() {
            if (window.contextVars.currentUser.id === self.user.pk) {
                self.editable = true;
                self.lastModified = Date();
                $(this).addClass('disabled');
                self.$input.removeClass('disabled');
                self.$saveComment.removeClass('disabled');
            } else {
                self.editable = false;
                $(this).addClass('disabled');
                self.$input.addClass('disabled');
                self.$saveComment.addClass('disabled');
                throw 'Only the author may edit this comment';
            }
        }
    });
    self.$deleteComment = $('<a>', {
        'class': 'btn fa fa-times',
        click: function() {
            if (window.contextVars.currentUser.id === self.user.pk) {
                self.editable = true;
                self.$input[0].value = '';
                self.$element.remove();
                self.$label.remove();

            } else {
                throw 'Only the author may delete this comment';
            }

        }
    });
    $control.append(self.$saveComment);
    $control.append(self.$editComment);
    $control.append(self.$deleteComment);
    $row.append($control);

    self.$element.append($row);
};
Comments.prototype.add = function() {
    var self = this;

    var comment = new self.Comment();
    self.comments.push(comment);
    self.$commentsList.append(comment.$element);
};

JSONEditor.defaults.editors.commentableString = JSONEditor.defaults.editors.string.extend({
    build: function() {
        var self = this;
        this._super();
        if (this.schema.help) {
            this.help = this.theme.getFormInputHelp(this.schema.help);
            $(this.input.previousSibling).after(this.help);
            $("#example").hide();
            $( ".example-block" ).click(function() {
                $("#example").slideToggle("slow");
            });
        };

        var $element = $('<div>', {
            'class': 'col-md-12 m-b-md'
        });
        $(this.input.parentNode).after($element);
        this.comments = new Comments($element);
    },
    getValue: function() {
        if (this.comments) {
            var comments = $.map(this.comments.comments, function(comment) {
                return {
                    value: comment.$input.val(),
                    user: comment.user,
                    lastModified: comment.lastModified
                };
            });

            for (var i = 0; i < comments.length; i++) {
                if (comments[i].value === '') {
                    comments.splice(i, 1);
                }
            }

            var val = {
                value: this._super(),
                comments: comments
            };
            return val;
        } else {
            return this._super();
        }
    }

});

/////////////// upload ////////////////

JSONEditor.defaults.options.upload = function(type, file, cbs) {
    // TODO may want to change this
    var nodeApiUrl = window.contextVars.node.urls.api;

    var tb = this;
    var redir = new URI(file.nodeUrl);
    redir.segment('files').segment(file.provider).segmentCoded(file.path.substring(1));
    var fileurl = redir.toString() + '/';

    if (type === 'root.upload_fail') cbs.failure('Upload failed');
    else {
        var tick = 0;
        var tickFunction = function() {
            tick += 1;
            if (tick < 100) {
                cbs.updateProgress(tick);
                window.setTimeout(tickFunction, 50);
            } else if (tick == 100) {
                cbs.updateProgress();
                window.setTimeout(tickFunction, 500);
            } else {
                cbs.success('/project' + fileurl);
            }
        };
        window.setTimeout(tickFunction);
    }
};

JSONEditor.defaults.resolvers.unshift(function(schema) {
    if (schema.type === 'string' && schema.format === 'url' && schema.options && schema.options.upload === true) {
        return 'myUpload';
    }
});

JSONEditor.defaults.editors.myUpload = JSONEditor.defaults.editors.upload.extend({
    build: function() {
        var self = this;
        this.title = this.header = this.label = this.theme.getFormInputLabel(this.getTitle());

        // Input that holds the base64 string
        this.input = this.theme.getFormInputField('hidden');
        this.container.appendChild(this.input);

        // Don't show uploader if this is readonly
        if (!this.schema.readOnly && !this.schema.readonly) {

            if (!this.jsoneditor.options.upload) {
                throw 'Upload handler required for upload editor';
            }

            // File uploader
            this.uploader = document.createElement('div');

            $(this.uploader).attr('id', 'registrationFilesGrid');

            this.uploader.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                folder = $(this).find($(event.target).attr('data-id'));
                if (!self.preview_value) {
                    self.refreshPreview();
                } else if (self.preview_value.kind === 'file') {
                    self.refreshPreview();
                    self.onChange(true);
                } else {
                    self.preview_value = undefined;
                    self.refreshPreview();
                }

            });
        }
        var description = this.schema.description;
        if (!description) {
            description = '';
        }

        this.preview = this.theme.getFormInputDescription(description);
        this.container.appendChild(this.preview);

        this.control = this.theme.getFormControl(this.label, this.uploader || this.input, this.preview);
        this.container.appendChild(this.control);

        var nodeApiUrl = window.contextVars.node.urls.api;
        var fangornOpts = {
            onselectrow: function(row, event) {
                self.preview_value = row.data;
                this.path = row.data.path;
                self.files = row.data;

                var tb = this;
                var redir = new URI(row.data.nodeUrl);
                redir.segment('files').segment(row.data.provider).segmentCoded(row.data.path.substring(1));
                var fileurl = redir.toString() + '/';
            }
        };

        this.filesWidget = new FilesWidget('registrationFilesGrid', nodeApiUrl + 'files/grid/', fangornOpts);
        this.filesWidget.init();

    },
    destroy: function() {
        //this.filesWidget.destroy();
    },
    refreshPreview: function() {
        if (this.last_preview === this.preview_value) return;
        this.last_preview = this.preview_value;

        this.preview.innerHTML = '';

        if (!this.preview_value) return;

        var self = this;

        var mime = this.preview_value.name.match(/^data:([^;,]+)[;,]/);
        if (mime) {
            mime = mime[1];
        } else {
            mime = 'unknown';
        }

        var file = this.files;

        this.preview.innerHTML = '<strong>Type:</strong> ' + mime + ', <strong>Size:</strong> ' + file.size + ' bytes';
        if (mime.substr(0, 5) === 'image') {
            this.preview.innerHTML += '<br>';
            var img = document.createElement('img');
            img.style.maxWidth = '100%';
            img.style.maxHeight = '100px';
            img.src = this.preview_value;
            this.preview.appendChild(img);
        }

        this.preview.innerHTML += '<br>';
        var uploadButton = this.getButton('Upload', 'upload', 'Upload');
        this.preview.appendChild(uploadButton);
        uploadButton.addEventListener('click', function(event) {
            event.preventDefault();

            uploadButton.setAttribute("disabled", "disabled");
            self.theme.removeInputError(self.uploader);

            if (self.theme.getProgressBar) {
                self.progressBar = self.theme.getProgressBar();
                self.preview.appendChild(self.progressBar);
            }

            self.jsoneditor.options.upload(self.path, file, {
                success: function(url) {
                    self.setValue(url);

                    if (self.parent) {
                        self.parent.onChildEditorChange(self);
                    } else {
                        self.jsoneditor.onChange();
                    }

                    if (self.progressBar) {
                        self.preview.removeChild(self.progressBar);
                    }
                    uploadButton.removeAttribute('disabled');
                },
                failure: function(error) {
                    self.theme.addInputError(self.uploader, error);
                    if (self.progressBar) {
                        self.preview.removeChild(self.progressBar);
                    }
                    uploadButton.removeAttribute('disabled');
                },
                updateProgress: function(progress) {
                    if (self.progressBar) {
                        if (progress) {
                            self.theme.updateProgressBar(self.progressBar, progress);
                        } else {
                            self.theme.updateProgressBarUnknown(self.progressBar);
                        }
                    }
                }
            });
        });
    }
});

// add for single select of check boxes
JSONEditor.defaults.resolvers.unshift(function(schema) {
    if (schema.type === "array" && schema.items && !(Array.isArray(schema.items)) && schema.uniqueItems && schema.items["enum"] && ['string', 'number', 'integer'].indexOf(schema.items.type) >= 0) {
        return "singleselect";
    }
});
JSONEditor.defaults.editors.singleselect = JSONEditor.defaults.editors.multiselect.extend({
    build: function() {

        var self = this,
            i;
        if (!this.options.compact) this.header = this.label = this.theme.getFormInputLabel(this.getTitle());
        if (this.schema.description) this.description = this.theme.getFormInputDescription(this.schema.description);

        if ((!this.schema.format && this.option_keys.length < 8) || this.schema.format === "checkbox") {
            this.input_type = 'checkboxes';

            this.inputs = {};
            this.controls = {};
            for (i = 0; i < this.option_keys.length; i++) {
                this.inputs[this.option_keys[i]] = this.theme.getCheckbox();
                this.select_options[this.option_keys[i]] = this.inputs[this.option_keys[i]];
                var label = this.theme.getCheckboxLabel(this.option_keys[i]);
                this.controls[this.option_keys[i]] = this.theme.getFormControl(label, this.inputs[this.option_keys[i]]);
            }

            this.control = this.theme.getMultiCheckboxHolder(this.controls, this.label, this.description);
        } else {
            this.input_type = 'select';
            this.input = this.theme.getSelectInput(this.option_keys);
            this.input.multiple = true;
            this.input.size = Math.min(10, this.option_keys.length);

            for (i = 0; i < this.option_keys.length; i++) {
                this.select_options[this.option_keys[i]] = this.input.children[i];
            }

            if (this.schema.readOnly || this.schema.readonly) {
                this.always_disabled = true;
                this.input.disabled = true;
            }

            this.control = this.theme.getFormControl(this.label, this.input, this.description);
        }

        this.container.appendChild(this.control);

        var previous;
        this.control.addEventListener("mouseover", function(e) {
            var new_value = [];
            for (i = 0; i < self.option_keys.length; i++) {
                if (self.select_options[self.option_keys[i]].selected || self.select_options[self.option_keys[i]].checked) {
                    new_value.push(self.select_values[self.option_keys[i]]);
                }
            }
            previous = new_value;

        });
        this.control.addEventListener('change', function(e) {
            e.preventDefault();
            e.stopPropagation();

            // delete older one using previous
            var new_value = [];
            for (i = 0; i < self.option_keys.length; i++) {
                if (self.select_options[self.option_keys[i]].selected || self.select_options[self.option_keys[i]].checked) {

                    var str = '"' + self.select_values[self.option_keys[i]] + '"';
                    var blah = self.select_values[self.option_keys[i]];
                    if (previous.indexOf(blah) != -1) {
                        self.select_options[self.option_keys[i]].checked = false;
                    } else {
                        new_value.push(self.select_values[self.option_keys[i]]);
                    }
                }
            }
            self.updateValue(new_value);
            self.onChange(true);
        });
    }
});
