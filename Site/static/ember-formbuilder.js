
(function(exports) {
(function() {
  var Bootstrap;

  Bootstrap = Ember.Mixin.create({
    wrapperTag: 'div',
    wrapperClass: 'control-group',
    inputWrapperTag: 'div',
    inputWrapperClass: 'controls',
    labelClass: 'control-label',
    helpTag: 'p',
    helpClass: 'help-block',
    errorTag: 'span',
    errorClass: 'help-inline',
    formClass: '',
    submitClass: 'btn btn-success',
    cancelClass: 'btn btn-danger',
    submitTag: 'button',
    cancelTag: 'a'
  });

  Ember.FormBuilder = Ember.Namespace.create({
    mixins: {
      'bootstrap': Bootstrap
    },
    pushMixin: function(mixin, mixinName) {
      return this.mixins[mixinName] = mixin;
    },
    getMixin: function(mixinName) {
      return this.mixins[mixinName];
    }
  });



























}).call(this);

})({});


(function(exports) {
(function() {

  Ember.Handlebars.registerHelper("cancel", function(text, options) {
    var _ref, _ref2;
    ember_assert("The cancel helper only takes a single argument", arguments.length <= 2);
    if (!options) {
      options = text;
      if (!options.hash.text) {
        text = ((_ref = Ember.FormBuilder.STRINGS) != null ? (_ref2 = _ref[this.objectName]) != null ? _ref2.cancel : void 0 : void 0) || 'Cancel';
      }
    }
    options.hash.preserveContext = false;
    options.hash.form = this;
    options.hash.text = text;
    return Ember.Handlebars.helpers.view.call(this, 'Ember.FormBuilder.Cancel', options);
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.Handlebars.registerHelper("formFor", function(object, options) {
    ember_assert("The formFor helper only takes a single argument", arguments.length <= 2);
    options.hash.contentBinding = object;
    options.hash.objectName = object;
    options.hash.parentView = this;
    options.hash.preserveContext = true;
    return Ember.Handlebars.helpers.view.call(this, 'Ember.FormBuilder.Form', options);
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.Handlebars.registerHelper("input", function(property, options) {
    var attribute, words, _i, _len, _ref, _ref2, _ref3, _ref4, _ref5, _ref6, _ref7;
    ember_assert("The input helper only takes a single argument", arguments.length <= 2);
    _ref = Ember.String.w('label hint placeholder');
    for (_i = 0, _len = _ref.length; _i < _len; _i++) {
      attribute = _ref[_i];
      if (!options.hash[attribute]) {
        options.hash[attribute] = (_ref2 = Ember.FormBuilder.STRINGS) != null ? (_ref3 = _ref2[this.objectName]) != null ? (_ref4 = _ref3[attribute + 's']) != null ? _ref4[property] : void 0 : void 0 : void 0;
        if (!options.hash[attribute]) {
          options.hash[attribute] = (_ref5 = Ember.FormBuilder.STRINGS) != null ? (_ref6 = _ref5.defaults) != null ? (_ref7 = _ref6[attribute + 's']) != null ? _ref7[property] : void 0 : void 0 : void 0;
        }
      }
    }
    if (!options.hash.label) {
      words = Ember.String.underscore(property).split('_');
      words = words.map(function(word) {
        return word.charAt(0).toUpperCase() + word.substring(1);
      });
      options.hash.label = words.join(' ');
    }
    options.hash.valueBinding = "content." + property;
    options.hash.name = property;
    options.hash.preserveContext = true;
    options.hash.form = this.form || this;
    return Ember.Handlebars.helpers.view.call(this, 'Ember.FormBuilder.Input', options);
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.Handlebars.registerHelper("submit", function(text, options) {
    var _ref, _ref2;
    ember_assert("The submit helper only takes a single argument", arguments.length <= 2);
    if (!options) {
      options = text;
      if (!options.hash.text) {
        text = ((_ref = Ember.FormBuilder.STRINGS) != null ? (_ref2 = _ref[this.objectName]) != null ? _ref2.submit : void 0 : void 0) || 'Submit';
      }
    }
    options.hash.preserveContext = false;
    options.hash.form = this;
    options.hash.text = text;
    return Ember.Handlebars.helpers.view.call(this, 'Ember.FormBuilder.Submit', options);
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.Cancel = Ember.View.extend({
    classNameBindings: ['classes'],
    template: Ember.Handlebars.compile('{{text}}'),
    init: function() {
      this._super();
      this.set('tagName', this.tagName || this.form.cancelTag);
      this.set('cancelClass', this.cancelClass || this.form.cancelClass);
      return this.set('classes', "" + this.cancelClass + " cancel-button");
    },
    click: function(event) {
      return this.form.parentView["" + this.form.objectName + "Cancel"](event);
    }
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.Checkbox = Ember.Checkbox.extend({
    tagName: '',
    id: Ember.computed(function() {
      return Ember.guidFor(this);
    }),
    defaultTemplate: Ember.Handlebars.compile('\
    <input type="checkbox"{{bindAttr id="id" name="name" checked="value" disabled="disabled"}}>\
  ')
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.Form = Ember.View.extend({
    tagName: 'form',
    classNameBindings: ['classes', 'formClass'],
    init: function() {
      this._super();
      this.set('mixin', this.mixin || 'bootstrap');
      return this.reopen(Ember.FormBuilder.getMixin(this.mixin));
    }
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.Input = Ember.View.extend({
    tagNameBinding: 'wrapperTag',
    classNameBindings: ['wrapperClass', 'infoClass'],
    inputClass: '',
    label: '',
    init: function() {
      this._super();
      this.set('inputView', this.inputView || 'Ember.FormBuilder.TextField');
      this.set('wrapperTag', this.wrapperTag || this.form.wrapperTag);
      this.set('wrapperClass', this.wrapperClass || this.form.wrapperClass);
      this.set('inputWrapperTag', this.inputWrapperTag || this.form.inputWrapperTag);
      this.set('inputWrapperClass', this.inputWrapperClass || this.form.inputWrapperClass);
      this.set('labelClass', this.labelClass || this.form.labelClass);
      this.set('helpTag', this.helpTag || this.form.helpTag);
      this.set('helpClass', this.helpClass || this.form.helpClass);
      this.set('errorTag', this.errorTag || this.form.errorTag);
      this.set('errorClass', this.errorClass || this.form.errorClass);
      if (this.showLabel === void 0) this.set('showLabel', true);
      if (this.showWrapper === void 0) this.set('showWrapper', true);
      if (!this.showWrapper) this.set('wrapperTag', '');
      if (Ember.empty(this.value)) this.set('value', '');
      this.errorChanged();
      return this.set('template', Ember.Handlebars.compile('\
      {{#if showWrapper}}\
        {{#if showLabel}}\
          <label {{bindAttr class="labelClass"}} for="' + Ember.guidFor(this) + 'input">\
            {{label}}\
          </label>\
        {{/if}}\
        {{#view Ember.View tagName=inputWrapperTag class=inputWrapperClass contentBinding="this"}}\
          ' + this.field() + '\
          {{#if content.error}}\
            {{#view Ember.View class=content.errorClass tagNameBinding="content.errorTag" contentBinding="content"}}\
              {{content.error}}\
            {{/view}}\
          {{/if}}\
          {{#if content.hint}}\
            {{#view Ember.View class=content.helpClass tagNameBinding="content.helpTag" contentBinding="content"}}\
              {{content.hint}}\
            {{/view}}\
          {{/if}}\
        {{/view}}\
      {{else}}\
        {{#view Ember.View tagName="" contentBinding="this"}}\
          ' + this.field() + '\
        {{/view}}\
      {{/if}}\
    '));
    },
    errorChanged: Ember.observer(function() {
      if (Ember.empty(this.error)) {
        return this.set('infoClass', '');
      } else {
        return this.set('infoClass', 'error');
      }
    }, 'error'),
    field: function() {
      switch (this.as) {
        case "select":
          return this.selectTag();
        case "checkboxes":
          return this.checkboxes();
        case "radioButtons":
          return this.radioButtons();
        case "text":
          this.set('inputView', 'Ember.FormBuilder.TextArea');
          return this.textInput();
        default:
          return this.textInput();
      }
    },
    textInput: function() {
      return '{{view ' + this.inputView + ' id="' + Ember.guidFor(this) + 'input"\
        name=content.name\
        placeholder=content.placeholder class=content.inputClass\
        valueBinding="content.value"}} ';
    },
    checkboxes: function() {
      return '{{#each content.collection contentBinding="this.content"}}\
        <label class="checkbox">\
          {{view Ember.FormBuilder.Checkbox name=content.name valueBinding="content.value"}}\
          {{label}}\
        </label>\
      {{/each}}';
    },
    radioButtons: function() {
      var group;
      group = "" + (Ember.guidFor(this)) + "group";
      return '{{#each content.collection}}\
        <label class="radio">\
          {{view Ember.FormBuilder.RadioButton\
            name=content.name\
            optionBinding="value"\
            valueBinding="parentView.content.value"\
            group="' + group + '"}}\
          {{label}}\
        </label>\
      {{/each}}';
    },
    selectTag: function() {
      var select;
      select = '{{view Ember.FormBuilder.Select\
                  name="content.name"\
                  contentBinding="content.collection"\
                  selectionBinding="content.name"\
                  optionLabelPath="content"\
                  optionValuePath="content"';
      if (this.prompt) select += ' prompt="' + this.prompt + '"';
      return select += '}}';
    }
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.RadioButton = Ember.View.extend({
    checked: false,
    group: "radio_button",
    disabled: false,
    classNames: ["ember-radio-button"],
    defaultTemplate: Ember.Handlebars.compile("    <input type=\"radio\" {{ bindAttr disabled=\"disabled\" name=\"group\" value=\"option\" checked=\"checked\"}} />  "),
    attributeBindings: ['name'],
    bindingChanged: (function() {
      if (this.get("option") === get(this, "value")) {
        return this.set("checked", true);
      }
    }).observes("value"),
    change: function() {
      return Ember.run.once(this, this._updateElementValue);
    },
    _updateElementValue: function() {
      var input;
      input = this.$("input:radio");
      return set(this, "value", input.attr("value"));
    }
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.Select = Ember.Select.extend({
    init: function() {
      this._super();
      return this.attributeBindings.push('name');
    }
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.Submit = Ember.View.extend({
    classNameBindings: ['classes'],
    template: Ember.Handlebars.compile('{{text}}'),
    init: function() {
      this._super();
      this.set('tagName', this.tagName || this.form.submitTag);
      this.set('submitClass', this.submitClass || this.form.submitClass);
      return this.set('classes', "" + this.submitClass + " submit-button");
    },
    click: function(event) {
      return this.form.parentView["" + this.form.objectName + "Submit"](event);
    }
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.TextArea = Ember.TextArea.extend({
    init: function() {
      this._super();
      return this.attributeBindings.push('name');
    }
  });

}).call(this);

})({});


(function(exports) {
(function() {

  Ember.FormBuilder.TextField = Ember.TextField.extend({
    init: function() {
      this._super();
      return this.attributeBindings.push('name');
    }
  });

}).call(this);

})({});


(function(exports) {
(function() {



}).call(this);

})({});
