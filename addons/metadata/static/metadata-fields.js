'use strict';

const $ = require('jquery');
const $osf = require('js/osfHelpers');
const oop = require('js/oop');
const _ = require('js/rdmGettext')._;
require('typeahead.js');


function createField(erad, question, valueEntry, callback) {
  if (question.type == 'string') {
    return createStringField(erad, question, (valueEntry || {}).value, callback);
  }
  if (question.type == 'choose') {
    return createChooseField(erad, question, (valueEntry || {}).value, callback);
  }
  throw new Error('Unsupported type: ' + question.type);
}

function validateField(erad, question, value) {
  if (!value) {
    if (question.required) {
      throw new Error(_("This field can't be blank."))
    }
    return;
  }
  if (question.type == 'string') {
    return validateStringField(erad, question, value);
  }
  if (question.type == 'choose') {
    return validateChooseField(erad, question, value);
  }
  throw new Error('Unsupported type: ' + question.type);
}

function createStringField(erad, question, value, callback) {
  if (question.format == 'text') {
    return new SingleElementField(
      createFormElement(function() {
        return $('<input></input>');
      }),
      question,
      value,
      callback
    );
  } else if (question.format == 'textarea') {
    return new SingleElementField(
      createFormElement(function() {
        return $('<textarea></textarea>');
      }),
      question,
      value,
      callback
    );
  }
  // TBD
  return new SingleElementField(
    createFormElement(function() {
      return $('<input></input>');
    }),
    question,
    value,
    callback
  );
}

function createChooseField(erad, question, value, callback) {
  if (question.format == 'singleselect') {
    return new SingleElementField(
      createFormElement(function() {
        return createChooser(question.options);
      }),
      question,
      value,
      callback
    );
  }
  // TBD
  return new SingleElementField(
    createFormElement(function() {
      return $('<input></input>');
    }),
    question,
    value,
    callback
  );
}

function validateStringField(erad, question, value) {
  // TBD
}

function validateChooseField(erad, question, value) {
  // TBD
}

function createChooser(options) {
  const select = $('<select></select>');
  select.append($('<option></option>').attr('value', '').text(_('Choose...')));
  (options || []).forEach(function(opt) {
    if (!opt.text) {
      const optElem = $('<option></option>').attr('value', opt).text(opt);
      select.append(optElem);
      return;
    }
    const optElem = $('<option></option>').attr('value', opt.text).text(opt.tooltip);
    select.append(optElem);
  });
  return select;
}

function createFormElement(createHandler) {
  return {
    create: function(callback) {
      const elem = createHandler();
      if (callback) {
        elem.change(callback);
      }
      return elem;
    },
    getValue: function(input) {
      return input.val();
    },
    setValue: function(input, value) {
      input.val(value);
    },
  };
}


function SingleElementField(formField, question, defaultValue, callback) {
  if (!question.qid) {
    throw new Error('No labels');
  }
  const self = this;

  self.formField = formField;
  self.label = question.qid;
  self.title = question.title;
  self.defaultValue = defaultValue;

  self.createFormGroup = function(input, errorContainer) {
    const label = $('<label></label>').text(self.title || self.label);
    if (question.required) {
      label.append($('<span></span>')
        .css('color', 'red')
        .css('font-weight', 'bold')
        .text('*'));
    }
    const group = $('<div></div>').addClass('form-group')
      .append(label)
      .append(input)
      .append(errorContainer);
    return group;
  }

  self.getValue = function(input) {
    return formField.getValue(input);
  };

  self.addElementTo = function(parent, errorContainer) {
    const input = formField.create(callback);
    input.addClass('form-control');
    if (self.defaultValue) {
      formField.setValue(input, self.defaultValue);
    }
    parent.append(self.createFormGroup(input, errorContainer));
    return input;
  };
}


/*function ERadResearcherNumberField(erad, label) {
  var self = this;
  self.baseTextField = new BaseTextField(label);
  self.label = label;

  self.addElementTo = function(parent) {
    var input = $('<input></input>').addClass('erad-researcher-number');

    var substringMatcher = function(candidates) {
      return function findMatches(q, cb) {
        var substrRegex = new RegExp(q, 'i');

        // iterate through the pool of strings and for any string that
        // contains the substring `q`, add it to the `matches` array

        var matches = (candidates || []).filter(function(c) {
          if (!c.kenkyusha_no) {
            return false;
          }
          return substrRegex.test(c.kenkyusha_no);
        });

        cb(matches);
      };
    };
    var container = $('<div></div>')
      .addClass('erad-researcher-number-container');
    parent.append(self.baseTextField.createFormGroup(container
      .append(input.addClass('form-control'))));
    input.typeahead({
      hint: false,
      highlight: true,
      minLength: 0
    },
    {
      display: function(data) {
        return data.kenkyusha_no;
      },
      templates: {
        suggestion: function(data) {
          return '<div style="background-color: white;"><span>' + $osf.htmlEscape(data.kenkyusha_shimei) + '</span> ' +
              '<span><small class="m-l-md text-muted">'+
              $osf.htmlEscape(data.kenkyukikan_mei) + ' - ' +
              $osf.htmlEscape(data.kadai_mei) + ' (' + data.nendo + ')'
              + '</small></span></div>';
        }
      },
      source: substringMatcher(erad.candidates),
    });

    input.bind('typeahead:selected', function(event, data) {
        console.log('selected', event, data);
        //if ( $.isFunction( settings.complete ) ) {
        //    settings.complete( event, data.value );
        //}
    });
    container.find('.twitter-typeahead').css('width', '100%');
    return input;
  };
}


function ERadResearcherNameField(erad, label) {
  var self = this;
  self.baseTextField = new BaseTextField(label);
  self.label = label;

  self.addElementTo = function(parent) {
    return self.baseTextField.addElementTo(parent);
  };
}*/


module.exports = {
  createField: createField,
  validateField: validateField
};
