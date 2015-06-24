var jedit = require('json-editor'); //TODO webpackify
var FilesWidget = require('js/FilesWidget');
var Fangorn = require('js/fangorn');
var $osf = require('js/osfHelpers');
var $ = require('jquery');

// var filesWidget = new FilesWidget('treeGrid', nodeApiUrl + 'files/grid/');
// filesWidget.init();

JSONEditor.defaults.options.upload = function() {
   // var filesWidget = new FilesWidget(this.input, nodeApiUrl + 'files/grid/');
    //filesWidget.init();
};

JSONEditor.defaults.resolvers.unshift(function(schema) {
    if(schema.type === "string" && schema.format === "url" && schema.options && schema.options.upload === true) {
        if(window.FileReader) return "myUpload";
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
        if(!this.schema.readOnly && !this.schema.readonly) {

        if(!this.jsoneditor.options.upload) throw "Upload handler required for upload editor";
        
        // File uploader
        //console.log(this.container);
        //this.uploader = filesWidget;
        this.uploader = document.createElement('div');
        //this.uploader = this.theme.getFormInputField('');
        //$(this.uploader).attr('class', 'form-control');
        $(this.uploader).attr('id', 'treeGrid');
        console.log(this.uploader);

        // var filesWidget = new FilesWidget('treeGrid', nodeApiUrl + 'files/grid/');
        // filesWidget.init();

        this.uploader.addEventListener('change',function(e) {
            e.preventDefault();
            e.stopPropagation();
        
            if(this.files && this.files.length) {
                var fr = new FileReader();
                fr.onload = function(evt) {
                    self.preview_value = evt.target.result;
                    self.refreshPreview();
                    self.onChange(true);
                    fr = null;
                };
                fr.readAsDataURL(this.files[0]);
            }
        });
    }
        var description = this.schema.description;
        if (!description) description = '';

        this.preview = this.theme.getFormInputDescription(description);
        this.container.appendChild(this.preview);

        this.control = this.theme.getFormControl(this.label, this.uploader||this.input, this.preview);
        this.container.appendChild(this.control);
    },
    postBuild: function() {
        var filesWidget = new FilesWidget('treeGrid', nodeApiUrl + 'files/grid/');
        filesWidget.init();
        console.log(this.container);    
    },
    refreshPreview: function() {
        if(this.last_preview === this.preview_value) return;
        this.last_preview = this.preview_value;

        this.preview.innerHTML = '';
        
        if(!this.preview_value) return;

        var self = this;

        var mime = this.preview_value.match(/^data:([^;,]+)[;,]/);
        if(mime) mime = mime[1];
        if(!mime) mime = 'unknown';

        var file = this.uploader.files[0];

        this.preview.innerHTML = '<strong>Type:</strong> '+mime+', <strong>Size:</strong> '+file.size+' bytes';
        if(mime.substr(0,5)==="image") {
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
        uploadButton.addEventListener('click',function(event) {
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

                    if(self.parent) self.parent.onChildEditorChange(self);
                    else self.jsoneditor.onChange();

                    if (self.progressBar) self.preview.removeChild(self.progressBar);
                    uploadButton.removeAttribute("disabled");
                },
                failure: function(error) {
                    self.theme.addInputError(self.uploader, error);
                    if (self.progressBar) self.preview.removeChild(self.progressBar);
                    uploadButton.removeAttribute("disabled");
                },
                updateProgress: function(progress) {
                    if (self.progressBar) {
                        if (progress) self.theme.updateProgressBar(self.progressBar, progress);
                        else self.theme.updateProgressBarUnknown(self.progressBar);
                    }
                }
            });
        });
    },
    setValue: function(val) {
        if(this.value !== val) {
            this.value = val;
            this.input.value = this.value;
            this.onChange();
        }
    },
    destroy: function() {
        if(this.preview && this.preview.parentNode) this.preview.parentNode.removeChild(this.preview);
        if(this.title && this.title.parentNode) this.title.parentNode.removeChild(this.title);
        if(this.input && this.input.parentNode) this.input.parentNode.removeChild(this.input);
        if(this.uploader && this.uploader.parentNode) this.uploader.parentNode.removeChild(this.uploader);

        this._super();
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

JSONEditor.defaults.editors.commentableString = JSONEditor.defaults.editors.string.extend({
    build: function() {
        this._super();

        $(this.input).after($('<span>Comments go here</span>'));
    }
});
