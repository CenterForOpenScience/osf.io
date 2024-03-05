'use strict';

/******************************************************************************************
 * QuestionPage has many QuestionField
 * QuestionField has a FormFieldInterface.
 *
 * QuestionPage has many questions form for a page. It does suggestion and autofill logic.
 * QuestionField has a form for a question. It has a FormFieldInterface and label, help, fill button.
 * Implementation of FormFieldInterface depends on question format and question type.
 * FormFieldInterface has many FormFieldInterface if question type is ArrayFormField or ObjectFormField.
 ******************************************************************************************/

const $ = require('jquery');
const $osf = require('js/osfHelpers');
const fangorn = require('js/fangorn');
const rdmGettext = require('js/rdmGettext');
const _ = rdmGettext._;
const sprintf = require('agh.sprintf').sprintf;
const datepicker = require('js/rdmDatepicker');
require('typeahead.js');
const oop = require('js/oop');
const Emitter = require('component-emitter');
const sift = require('sift').default;
const util = require('./util');
const sizeofFormat = require("./util").sizeofFormat;
const getLocalizedText = util.getLocalizedText;
const normalizeText = util.normalizeText;

const logPrefix = '[metadata] ';


const QuestionPage = oop.defclass({
  constructor: function(schema, fileItem, options) {
    const self = this;
    self.schema = schema;
    self.fileItem = fileItem;
    self.options = options;
    self.fields = [];
    self.hasValidationError = false;
  },

  create: function() {
    const self = this;
    self.fields = [];
    const fileItemData = self.options.multiple ? {} : self.fileItem.data || {};
    (self.schema.pages || []).forEach(function(page) {
      (page.questions || []).forEach(function(question) {
        if (!question.qid || !question.qid.match(/^grdm-file:.+/)) {
          return;
        }
        const value = (fileItemData[question.qid] || {}).value;
        const field = createQuestionField(
          question,
          value,
          self.options
        );
        field.on('change', function() {
          self.validateAll();
        });
        field.on('suggestionSelected', function(suggestion, tree) {
          const nextTree = tree.concat([self]);
          if (suggestion.suggestion.autofill) {
            self.suggestionAutofill(suggestion, nextTree);
          }
        });
        self.fields.push(field);
      });
    });
    return self.fields;
  },

  suggestionAutofill: function(suggestion, tree) {
    const self = this;
    const autofillMap = suggestion.suggestion.autofill;
    Object.keys(autofillMap).forEach(function(path) {
      const field = self._findFieldFromTree(path, tree.slice(1));
      if (!field) {
        throw new Error('No field for path: ' + path);
      }
      const value = suggestion.value[autofillMap[path]];
      if (value != null) {
        field.setValue(value);
      }
    });
  },

  _findFieldFromTree: function(path, tree) {
    var node = tree.shift();
    while (path && path.startsWith('../')) {
      node = tree.shift();
      path = path.substring(3);
    }
    return node.fields.find(function(field) {
      return field.question.qid === path || field.question.id === path;
    });
  },

  // required_if and enabled_if are not full supported for hierarchical fields.
  validateAll: function() {
    const self = this;
    self.hasValidationError = false;
    self.fields.forEach(function(field) {
      const error = self._validateQuestionField(field, self.fields, self.options);
      if (error) {
        self.hasValidationError = true;
      }
      field.showError();
      self._updateEnabledQuestionField(field, self.fields);
    });
  },

  _validateQuestionField: function(questionField, questionFields, options) {
    questionField.lastError = null;
    function walk(field, fields) {
      try {
        validateField(field.question, field.getValue(), fields, options);
      } catch (error) {
        if (field !== questionField.formField) {
          questionField.lastError = new Error('[' + getLocalizedText(field.question.title) + '] ' + error.message);
        } else {
          questionField.lastError = error;
        }
        return;
      }
      if (field instanceof ObjectFormField) {
        field.fields.forEach(function (childField) {
          walk(childField, field.fields);
        });
      } else if (field instanceof ArrayFormField) {
        field.fields.forEach(function (row) {
          row.forEach(function (childField) {
            walk(childField, row);
          });
        });
      }
    }
    walk(questionField.formField, questionFields.map(function(qf) {
      return qf.formField;
    }));
    return questionField.lastError;
  },

  _updateEnabledQuestionField: function(questionField, questionFields) {
    const cond = questionField.question.enabled_if;
    questionField.updateEnabled(!cond || evaluateCond(cond, questionFields));
  },
});


function createQuestionField(question, value, options) {
  const formField = createFormField(question, options, value);
  const questionForm = new QuestionField(formField, question, options);
  questionForm.create();
  return questionForm;
}

const QuestionField = oop.extend(Emitter, {
  constructor: function(formField, question, options) {
    if (!question.qid) {
      throw new Error('No labels');
    }
    this.super.constructor.call(this, {});
    const self = this;
    self.formField = formField;
    self.question = question;
    self.options = options;
    self.element = null;
    self.clearField = null;
    self.errorContainer = null;
    self.isDisplayedHelp = false;
    self.lastError = null;
    self.enabled = true;
  },

  create: function() {
    const self = this;
    self.element = $('<div></div>').addClass('form-group');

    // construct header
    const header = $('<div></div>');
    self.element.append(header);

    // construct label
    const label = $('<label></label>')
      .text(self.question.title ? getLocalizedText(self.question.title) : self.question.label);
    if (self.question.required) {
      label.append($('<span></span>')
        .css('color', 'red')
        .css('font-weight', 'bold')
        .text('*'));
    }
    header.append(label);

    // construct clear field
    if (self.options.multiple) {
      const clearId = 'clear-' + self.question.qid.replace(':', '-');
      self.clearField = $('<input></input>')
        .addClass('form-check-input')
        .addClass('metadata-form-clear-checkbox')
        .attr('type', 'checkbox')
        .attr('id', clearId);
      const clearLabel = $('<label></label>')
        .addClass('form-check-label')
        .attr('for', clearId)
        .text(_('Clear'));
      const clearFormBlock = $('<div></div>')
        .addClass('form-check')
        .css('float', 'right')
        .append(self.clearField)
        .append(clearLabel);
      self.clearField.on('change', function() {
        if (self.clearField.checked()) {
          self.formField.reset(input);
          self.formField.disable(input, true);
        } else {
          self.formField.disable(input, false);
        }
      });
      header.append(clearFormBlock);
    }

    // construct help
    if (self.question.help) {
      self.isDisplayedHelp = false;
      const helpLink = $('<a></a>')
        .addClass('help-toggle-button')
        .text(_('Show example'));
      const helpLinkBlock = $('<p></p>').append(helpLink);
      const help = $('<p></p>')
        .addClass('help-block')
        .text(getLocalizedText(self.question.help))
        .hide();
      helpLink.on('click', function (e) {
        e.preventDefault();
        if (self.isDisplayedHelp) {
          helpLink.text(_('Show example'));
          help.hide();
          self.isDisplayedHelp = false;
        } else {
          helpLink.text(_('Hide example'));
          help.show();
          self.isDisplayedHelp = true;
        }
      });
      self.element.append(helpLinkBlock).append(help);
    }

    // construct form field
    self.element.append(self.formField.container)
    self.formField.on('change', function(value) {
      self.emit('change', value);
    });
    self.formField.on('suggestionSelected', function(suggestion, tree) {
      self.emit('suggestionSelected', suggestion, tree);
    });

    // construct error container
    self.errorContainer = $('<div></div>')
      .css('color', 'red').hide();
    self.element.append(self.errorContainer);

    return self.element;
  },

  getValue: function() {
    const self = this;
    return self.formField.getValue();
  },

  setValue: function(value) {
    const self = this;
    self.formField.setValue(value);
  },

  checkedClear: function() {
    const self = this;
    return self.clearField && self.clearField.checked;
  },

  showError: function() {
    const self = this;
    if (self.lastError) {
      self.errorContainer.text(self.lastError.message).show();
    } else {
      self.errorContainer.hide().text('');
    }
  },

  updateEnabled: function(enabled) {
    const self = this;
    self.enabled = enabled;
    if (self.enabled) {
      self.element.show();
    } else {
      self.element.hide();
    }
  },
});

function createFormField(question, options, value) {
  var formField;
  if (question.type === 'object') {
    formField = new ObjectFormField(question, options);
  } else if (question.type === 'array') {
    formField = new ArrayFormField(question, options);
  } else if (question.format === 'text') {
    formField = new TextFormField(question, options);
  } else if (question.format === 'textarea') {
    formField = new TextareaFormField(question, options);
  } else if (question.format === 'date') {
    formField = new DatePickerFormField(question, options);
  } else if (question.format === 'singleselect') {
    formField = new SingleSelectFormField(question, options);
  } else {
    console.error(logPrefix + 'Unknown format: ' + question.format);
    formField = new TextFormField(question, options);
  }
  formField.create();
  try {
    formField.setValue(value);
  } catch (error) {
    console.error('Cannot set default value for question ' + question.qid + ': ' + error.message, value);
  }
  return formField;
}

const noImplementation = function() {
  throw new Error('no implementation');
}
const FormFieldInterface = oop.extend(Emitter, {
  constructor: function() {
    this.super.constructor.call(this, {});
    this.container = null;
  },
  create: noImplementation,
  getValue: noImplementation,
  setValue: noImplementation,
  reset: noImplementation,
  disable: noImplementation,
});

const TextFormField = oop.extend(FormFieldInterface, {
  constructor: function(question, options) {
    const self = this;
    self.question = question;
    self.options = options || {};
    self.container = null;
    self.input = null;
    self.usedTypeahead = false;
  },

  create: function() {
    const self = this;
    self.input = $('<input/>')
      .addClass('form-control');
    if (self.options.readonly) {
      self.input.attr('readonly', true);
    }
    self.input.change(function(event) {
      const value = event.target.value;
      if (value && self.question.space_normalization) {
        const normalized = normalizeText(value);
        if (value !== normalized) {
          self.setValue(normalized);
          return;
        }
      }
      self.emit('change', event.target.value);
    });
    self.container = $('<div>').append(self.input);

    const buttonSuggestions = (self.question.suggestion || []).filter(function (suggestion) {
      return suggestion.button;
    });
    if (!self.options.readonly && !self.options.multiple && buttonSuggestions.length) {
      function onSuggested(value) {
        self.setValue(value);
      }
      function enteredValue() {
        const value = self.getValue();
        return value != null && value !== '';
      }
      const suggestionContainer = createSuggestionButton(
        self.question, buttonSuggestions, self.options,
        onSuggested, enteredValue
      );
      self.container
        .css('display', 'flex')
        .append(suggestionContainer);
    }

    const templateSuggestions = (self.question.suggestion || []).filter(function (suggestion) {
      return suggestion.template;
    });
    if (!self.options.readonly && !self.options.multiple && templateSuggestions.length) {
      self.input.typeahead(
        {
          hint: false,
          highlight: true,
          minLength: 0
        },
        {
          display: function(data) {
            return data.display;
          },
          templates: {
            suggestion: function(data) {
              return data.template;
            }
          },
          source: $osf.throttle(function (q, cb) {
            suggestForTypeahead(self.question, templateSuggestions, q, self.options)
              .then(function (results) {
                cb(results.flat());
              }).catch(function () {
                console.error(error);
                cb([]);
              });
          }, 500, {leading: false}),
        }
      )
      self.input.bind('typeahead:selected', function(event, data) {
        self.emit('suggestionSelected', data, [self]);
      });
      self.container.find('.twitter-typeahead').css('width', '100%');
      self.usedTypeahead = true;
    }
  },

  getValue: function() {
    const self = this;
    return self.input.val();
  },

  setValue: function(value) {
    const self = this;
    if (self.getValue() === '' && value === '') {
      // to avoid typehead bug
      return;
    }
    if (self.usedTypeahead) {
      self.input.typeahead('val', value).change();
    } else {
      self.input.val(value);
    }
  },

  reset: function() {
    const self = this;
    self.input.val(null);
  },

  disable: function(disabled) {
    const self = this;
    self.input.attr('disabled', disabled);
  },
});

const TextareaFormField = oop.extend(FormFieldInterface, {
  constructor: function(question, options) {
    const self = this;
    self.question = question;
    self.options = options || {};
    self.container = null;
    self.input = null;
  },

  create: function() {
    const self = this;
    self.input = $('<textarea></textarea>')
      .addClass('form-control');
    if (self.options.readonly) {
      self.input.attr('readonly', true);
    }
    self.input.change(function(event) {
      const value = event.target.value;
      if (value && self.question.space_normalization) {
        const normalized = normalizeText(value);
        if (value !== normalized) {
          self.setValue(normalized);
          return;
        }
      }
      self.emit('change', event.target.value);
    });
    self.container = self.input;
  },

  getValue: function() {
    const self = this;
    return self.input.val();
  },

  setValue: function(value) {
    const self = this;
    self.input.val(value);
  },

  reset: function() {
    const self = this;
    self.input.val(null);
  },

  disable: function(disabled) {
    const self = this;
    self.input.attr('disabled', disabled);
  },
});

const DatePickerFormField = oop.extend(FormFieldInterface, {
  constructor: function(question, options) {
    const self = this;
    self.question = question;
    self.options = options || {};
    self.container = null;
    self.input = null;
  },

  create: function() {
    const self = this;
    self.input = $('<input></input>')
      .addClass('datepicker')
      .addClass('form-control');
    datepicker.mount(self.input, null);
    if (self.options.readonly) {
      self.input.attr('readonly', true);
    }
    self.input.change(function(event) {
      self.emit('change', event.target.value);
    });
    self.container = self.input;
  },

  getValue: function() {
    const self = this;
    return self.input.val();
  },

  setValue: function(value) {
    const self = this;
    self.input.datepicker('update', value);
  },

  reset: function() {
    const self = this;
    self.input.val(null);
  },

  disable: function(disabled) {
    const self = this;
    self.input.attr('disabled', disabled);
  },
});

const SingleSelectFormField = oop.extend(FormFieldInterface, {
  constructor: function(question, options) {
    const self = this;
    self.question = question;
    self.options = options || {};
    self.container = null;
    self.select = null;
  },

  create: function() {
    const self = this;
    self.select = $('<select></select>')
      .addClass('form-control');
    if (self.options.readonly) {
      self.select.attr('readonly', true);
    }
    const defaultOption = $('<option></option>').attr('value', '');
    if (self.options.multiple) {
      defaultOption.text(_('(Not Modified)'));
      defaultOption.attr('selected', true)
    } else {
      defaultOption.text(_('Choose...'));
    }
    self.select.append(defaultOption);
    var groupElem = null;
    (self.question.options || []).forEach(function(opt) {
      if (opt.text && opt.text.startsWith('group:None:')) {
        groupElem = null;
      } else if (opt.text && opt.text.startsWith('group:')) {
        groupElem = $('<optgroup></optgroup>').attr('label', getLocalizedText(opt.tooltip));
        self.select.append(groupElem);
      } else {
        const optElem = $('<option></option>')
          .attr('value', opt.text === undefined ? opt : opt.text)
          .text(opt.text === undefined ? opt : getLocalizedText(opt.tooltip));
        if (!self.options.multiple && opt.default) {
          optElem.attr('selected', true);
        }
        if (groupElem) {
          groupElem.append(optElem);
        } else {
          self.select.append(optElem);
        }
      }
    });
    self.select.change(function(event) {
      self.emit('change', event.target.value);
    });
    self.container = self.select;
  },

  getValue: function() {
    const self = this;
    return self.select.val();
  },

  setValue: function(value) {
    const self = this;
    self.select.val(value);
  },

  reset: function() {
    const self = this;
    self.select.val(null);
  },

  disable: function(disabled) {
    const self = this;
    self.select.attr('disabled', disabled);
  },
});

const ArrayFormField = oop.extend(FormFieldInterface, {
  constructor: function(question, options) {
    const self = this;
    self.question = question;
    self.fields = [];  // subquestions
    self.options = options || {};
    self.container = null;
    self.tbody = null;
    self.emptyLine = null;
  },

  create: function() {
    const self = this;

    const headRow = $('<tr>');
    const thead = $('<thead>').append(headRow);
    self.question.properties.forEach(function(prop) {
      headRow.append($('<th>' + getLocalizedText(prop.title) + '</th>'));
    });
    headRow.append($('<th>'));  // remove button header

    self.emptyLine = $('<td></td>')
      .attr('colspan', '4')
      .css('text-align', 'center')
      .css('padding', '1em')
      .text(_('No data'))
      .show();
    self.tbody = $('<tbody>').append(self.emptyLine);

    const table = $('<table class="table responsive-table responsive-table-xxs">')
      .append(thead)
      .append(self.tbody);
    self.container = $('<div>').append(table);
    if (!self.options || !self.options.readonly) {
      const addButton = $('<a class="btn btn-success btn-sm">')
        .append($('<i class="fa fa-plus"></i>'))
        .append($('<span></span>').text(_('Add')));
      addButton.on('click', function (e) {
        e.preventDefault();
        self.addRow();
        self.emit('change', self.getValue());
      });
      self.container.append(addButton);
    }
  },

  addRow: function(value) {
    const self = this;
    const subFormFields = self.question.properties.map(function(prop) {
      const subFormField = createFormField(prop, self.options);
      subFormField.create();
      if (value && value[prop.id]) {
        subFormField.setValue(value[prop.id]);
      }
      subFormField.on('change', function() {
        self.emit('change', self.getValue());
      });
      return subFormField;
    });
    subFormFields.forEach(function(subFormField) {
      subFormField.on('suggestionSelected', function(suggestion, tree) {
        const nextTree = tree.concat([
          {fields: subFormFields},
          self,
        ]);
        self.emit('suggestionSelected', suggestion, nextTree);
      });
    });
    const tr = $('<tr>');
    subFormFields.forEach(function(subFormField) {
      tr.append($('<td>').append(subFormField.container));
    });
    if (!self.options || !self.options.readonly) {
      const removeButton = $('<span class="remove-row"><i class="fa fa-times fa-2x remove-or-reject"></i></span>');
      removeButton.on('click', function (e) {
        e.preventDefault();
        self.removeRow(subFormFields, tr);
        self.emit('change', self.getValue());
      });
      tr.append($('<td>').append(removeButton));
    }
    self.tbody.append(tr);
    self.emptyLine.hide();
    self.fields.push(subFormFields);
  },

  removeRow: function(subquestion, tr) {
    const self = this;
    tr.remove();
    self.fields.splice(self.fields.indexOf(subquestion), 1);
    if (self.fields.length === 0) {
      self.emptyLine.show();
    }
  },

  getValue: function() {
    const self = this;
    const res = [];
    self.fields.forEach(function(subquestionGroup) {
      const row = {};
      subquestionGroup.forEach(function(subquestion) {
        row[subquestion.question.id] = subquestion.getValue();
      });
      if (Object.values(row).some(function(value) {
        return value !== null && value !== '';
      })) {
        res.push(row);
      }
    });
    return res;
  },

  setValue: function(value) {
    const self = this;
    self.reset();
    var rows = [];
    if (value && typeof value === 'string') {
      rows = JSON.parse(value);
    } else {
      rows = value || [];
    }
    rows.forEach(function(row) {
      self.addRow(row);
    });
  },

  reset: function() {
    const self = this;
    self.tbody.empty();
    self.fields = [];
  },

  disable: function(disabled) {
    const self = this;
    self.fields.forEach(function(subquestionGroup) {
      subquestionGroup.forEach(function(subquestion) {
        subquestion.disable(disabled);
      });
    });
    const btn = self.container.find('.btn');
    if (disabled) {
      btn.addClass('disabled');
    } else {
      btn.removeClass('disabled');
    }
  },
});

const ObjectFormField = oop.extend(FormFieldInterface, {
  constructor: function(question, options) {
    const self = this;
    self.question = question;
    self.fields = [];  // subquestions
    self.options = options || {};
    self.container = null;
    self.tbody = null;
  },

  create: function() {
    const self = this;
    const headRow = $('<tr>');
    const thead = $('<thead>').append(headRow);
    self.question.properties.forEach(function(prop) {
      headRow.append($('<th>' + getLocalizedText(prop.title) + '</th>'));
    });

    self.fields = self.question.properties.map(function(prop) {
      const subFormField = createFormField(prop, self.options);
      subFormField.create();
      subFormField.on('change', function() {
        self.emit('change', self.getValue());
      });
      subFormField.on('suggestionSelected', function(suggestion, tree) {
        const nextTree = tree.concat([self]);
        self.emit('suggestionSelected', suggestion, nextTree);
      });
      return subFormField;
    });
    const tr = $('<tr>');
    self.fields.forEach(function(subFormField) {
      tr.append($('<td>').append(subFormField.container));
    });
    const tbody = $('<tbody>').append(tr);

    const table = $('<table class="table responsive-table responsive-table-xxs" style="margin-bottom: 0">')
      .append(thead)
      .append(tbody);
    self.container = $('<div>').append(table);
  },

  getValue: function() {
    const self = this;
    const res = {};
    self.fields.forEach(function(subquestion) {
      res[subquestion.question.id] = subquestion.getValue();
    });
    if (Object.values(res).some(function(value) {
      return value !== null && value !== '';
    })) {
      return res;
    }
    return null;
  },

  setValue: function(value) {
    const self = this;
    self.reset();
    var rows = value || {};
    if (typeof(value) === 'string') {
      rows = JSON.parse(value);
    }
    self.fields.forEach(function(subquestion) {
      const value = rows[subquestion.question.id];
      subquestion.setValue(value);
    });
  },

  reset: function() {
    const self = this;
    self.fields.forEach(function (subquestion) {
      subquestion.reset();
    });
  },

  disable: function(disabled) {
    const self = this;
    self.fields.forEach(function (subquestion) {
      subquestion.disable(disabled);
    });
  },
});



/// validation

function validateField(question, value, questionFields, options) {
  const multiple = (options || {}).multiple;
  validateRequired(question, value, questionFields, multiple);
  validatePattern(question, value);
}

function validatePattern(question, value) {
  if (question.pattern && value && !(new RegExp(question.pattern).test(value))) {
    throw new Error(_("Please enter the correct value. ") + getLocalizedText(question.help));
  }
}

function validateRequired(question, value, questionFields, multiple) {
  if (multiple || value) {
    return;
  }
  if (question.enabled_if && !evaluateCond(question.enabled_if, questionFields)) {
    return;
  }
  const cond = question.required_if;
  const condErrorMessage = question.message_required_if;
  if (cond) {
    if (typeof(cond) === 'string') {
      const otherField = questionFields.find(function(questionField) {
        return questionField.question.qid === cond || questionField.question.id === cond;
      });
      if (!otherField) {
        throw new Error('Schema error: invalid required_if: ' + cond);
      }
      if (!otherField.getValue()) {
        throw new Error(
          condErrorMessage ||
          sprintf(_('One of this field or "%s" field must be filled.'),
            getLocalizedText(otherField.question.title))
        );
      }
    } else if (typeof(cond) === 'object') {
      if (evaluateCond(cond, questionFields)) {
        if (!condErrorMessage) {
          throw new Error('Schema error: required message_required_if');
        }
        throw new Error(getLocalizedText(condErrorMessage));
      }
    } else {
      throw new Error('Schema error: invalid required_if: ' + cond);
    }
  } else if (question.required) {
    throw new Error(_("This field can't be blank."));
  }
}


// suggestion

function requestSuggestion(filepath, key, keyword) {
  var url = contextVars.node.urls.api + 'metadata/file_metadata/suggestions/' + encodeURI(filepath);
  return $.ajax({
    url: url,
    type: 'GET',
    dataType: 'json',
    data: {
      key: key,
      keyword: keyword
    }
  }).catch(function(xhr, status, error) {
    Raven.captureMessage('Error while retrieving file metadata suggestions', {
      extra: {
        url: url,
        status: status,
        error: error
      }
    });
    return Promise.reject({xhr: xhr, status: status, error: error});
  }).then(function (data) {
    const res = ((data.data || {}).attributes || {}).suggestions || [];
    console.log(logPrefix, 'suggestion: ', res);
    return res;
  });
}

function suggestForButton(question, suggestion, options) {
  if (suggestion.key === 'file-size') {
    const wbcache = options.wbcache;
    const filepath = options.filepath;
    wbcache.clearCache();
    const task = filepath.endsWith('/') ?
      wbcache.listFiles(filepath, true)
        .then(function (files) {
          return files.reduce(function(y, x) {
            return y + Number(x.item.attributes.size);
          }, 0);
        }) :
      new Promise(function (resolve, reject) {
        try {
          wbcache.searchFile(filepath, function (item) {
            resolve(Number(item.attributes.size));
          });
        } catch (err) {
          reject(err);
        }
      });
    return task
      .then(function (totalSize) {
        return sizeofFormat(totalSize);
      })
  } else if (suggestion.key === 'file-url') {
    return Promise.resolve(fangorn.getPersistentLinkFor(options.fileitem));
  } else { // for key === file-data-number
    const fileitem = options.fileitem;
    const itemUrl = fangorn.getPersistentLinkFor(fileitem);
    const filepath = itemUrl.substr(itemUrl.indexOf('files/'));
    return requestSuggestion(filepath, suggestion.key)
      .then(function (suggestions) {
        return (suggestions.find(function (s) { return s.key === suggestion.key}) || {}).value;
      });
  }
}

function suggestForTypeahead(question, templateSuggestions, keyword, options) {
  const fileitem = options.fileitem;
  const itemUrl = fangorn.getPersistentLinkFor(fileitem);
  const filepath = itemUrl.substr(itemUrl.indexOf('files/'));
  const keys = templateSuggestions.map(function (suggestion) { return suggestion.key; });
  return requestSuggestion(filepath, keys, keyword)
    .then(function (results) {
      return results.map(function (result) {
        const suggestion = templateSuggestions.find(function (s) { return s.key === result.key; });
        if (!suggestion) {
          return null;
        }
        const template = Object.keys(result.value).reduce(function (template, key) {
          return template.replaceAll('{{' + key + '}}', result.value[key]);
        }, suggestion.template);
        const display = result.value.hasOwnProperty(result.key) ?
          result.value[result.key] :
          result.value[(suggestion.autofill || {})[question.qid]];
        return {
          template: template,
          display: display,
          value: result.value,
          suggestion: suggestion,
        }
      }).filter(function(result) {
        return result;
      });
    });
}

function createSuggestionButton(question, buttonSuggestions, options, onSuggested, enteredValue) {
  const suggestionContainer = $('<div>')
    .css('margin', 'auto 0 auto 8px');
  buttonSuggestions.forEach(function(suggestion) {
    const errorContainer = $('<span>')
      .css('color', 'red').hide();
    const indicator = $('<i class="fa fa-spinner fa-pulse">')
      .hide();
    const button = $('<a class="btn btn-default btn-sm">')
      .append($('<i class="fa fa-refresh"></i>'))
      .append($('<span></span>').text(getLocalizedText(suggestion.button)))
      .append(indicator);
    var processing = false;
    button.on('click', function (e) {
      e.preventDefault();
      if (enteredValue() && !window.confirm(_('Overwrite already entered value?'))) {
        return;
      }
      if (!processing) {
        processing = true;
        button.attr('disabled', true);
        errorContainer.hide().text('');
        indicator.show();
        suggestForButton(question, suggestion, options)
          .then(function (value) {
            onSuggested(value);
          })
          .catch(function (err) {
            console.error(err);
            Raven.captureMessage(_('Could not list files'), {
              extra: {
                error: err.toString()
              }
            });
            errorContainer.text('Suggestion error: ' + err).show();
          })
          .then(function () {
            processing = false;
            button.attr('disabled', false);
            indicator.hide();
          });
      }
    });
    suggestionContainer
      .append(button)
      .append(errorContainer);
  });
  return suggestionContainer;
}


// helper

function evaluateCond(cond, questionFields) {
  const values = {};
  questionFields.forEach(function(field) {
    const value = field.getValue();
    if (value != null && value !== '') {
      values[field.question.qid] = value;
    }
  });
  return sift(cond)(values);
}


module.exports = {
  QuestionPage: QuestionPage,
};
