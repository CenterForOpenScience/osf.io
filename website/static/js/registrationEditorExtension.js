var jedit = require('json-editor'); //TODO webpackify

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
