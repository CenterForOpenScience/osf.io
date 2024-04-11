'use strict';

const $ = require('jquery');
const $osf = require('js/osfHelpers');
const fangorn = require('js/fangorn');
const rdmGettext = require('js/rdmGettext');
const _ = rdmGettext._;
const datepicker = require('js/rdmDatepicker');
require('typeahead.js');

const logPrefix = '[metadata] ';

function getLocalizedText(text) {
  if (!text) {
    return text;
  }
  if (!text.includes('|')) {
    return text;
  }
  const texts = text.split('|');
  if (rdmGettext.getBrowserLang() === 'ja') {
    return texts[0];
  }
  return texts[1];
}

function createField(erad, fileMetadataSuggestion, question, valueEntry, options, onChange) {
  if (question.type == 'string') {
    return createStringField(erad, fileMetadataSuggestion, question, (valueEntry || {}).value, options, onChange);
  }
  if (question.type == 'choose') {
    return createChooseField(erad, fileMetadataSuggestion, question, (valueEntry || {}).value, options, onChange);
  }
  throw new Error('Unsupported type: ' + question.type);
}

function validateField(erad, question, value, fieldSetAndValues, options) {
  const multiple = (options || {}).multiple;
  if (!multiple && question.qid == 'grdm-file:available-date') {
    return validateAvailableDateField(erad, question, value, fieldSetAndValues);
  }
  if (!multiple && question.qid == 'grdm-file:data-man-email') {
    return validateContactManagerField(erad, question, value, fieldSetAndValues);
  }
  if (!value) {
    if (question.required && !multiple) {
      throw new Error(_("This field can't be blank."))
    }
    return;
  }
  if (question.qid == 'grdm-file:creators') {
    return validateCreators(erad, question, value);
  }
  if (question.type == 'string') {
    return validateStringField(erad, question, value);
  }
  if (question.type == 'choose') {
    return validateChooseField(erad, question, value);
  }
  throw new Error('Unsupported type: ' + question.type);
}

function createStringField(erad, fileMetadataSuggestion, question, value, options, onChange) {
  if (question.format == 'text') {
    return new SingleElementField(
      createFormElement(function() {
        return $('<input></input>');
      }, question, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (question.format == 'textarea') {
    return new SingleElementField(
      createFormElement(function() {
        return $('<textarea></textarea>');
      }, question, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (question.format == 'date') {
    return new SingleElementField(
      createFormElement(function() {
        const elem = $('<input></input>').addClass('datepicker');
        datepicker.mount(elem, null);
        return elem;
      }, question, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (question.format == 'file-creators') {
    return new SingleElementField(
      createFileCreatorsFieldElement(erad, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (question.format == 'e-rad-researcher-number') {
    return new SingleElementField(
      createERadResearcherNumberFieldElement(erad, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (
    question.format == 'e-rad-researcher-name-ja' ||
    question.format == 'e-rad-researcher-name-en' ||
    question.format == 'file-institution-identifier'
  ) {
    return new SingleElementField(
      createFormElement(function() {
        return $('<input></input>').addClass(question.format);
      }, question, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (question.format == 'file-capacity') {
    return new SingleElementField(
      createFileCapacityFieldElement(function() {
        return $('<input></input>');
      }, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (question.format == 'file-data-number') {
    return new SingleElementField(
      createDataNoFieldElement(function() {
        return $('<input></input>');
      }, fileMetadataSuggestion, question, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (question.format == 'file-url') {
    return new SingleElementField(
      createFileURLFieldElement(function() {
        return $('<input></input>');
      }, options),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  } else if (
    question.format == 'file-institution-ja' ||
    question.format == 'file-institution-en'
  ) {
    return new SingleElementField(
      createFileInstitutionFieldElement(options, question.format),
      (options && options.multiple) ? createClearFormElement(question) : null,
      question,
      value,
      options,
      onChange
    );
  }
  return new SingleElementField(
    createFormElement(function() {
      return $('<input></input>');
    }, question, options),
    (options && options.multiple) ? createClearFormElement(question) : null,
    question,
    value,
    options,
    onChange
  );
}

function createChooseField(erad, fileMetadataSuggestion, question, value, options, onChange) {
  if (question.format == 'singleselect') {
    return new SingleElementField(
      createFormElement(function() {
        return createChooser(question, options);
      }, question, options),
      null,
      question,
      value,
      options,
      onChange
    );
  }
  return new SingleElementField(
    createFormElement(function() {
      return $('<input></input>');
    }, question, options),
    null,
    question,
    value,
    options,
    onChange
  );
}

function validateStringField(erad, question, value) {
  if (question.pattern && !(new RegExp(question.pattern).test(value))) {
    throw new Error(_("Please enter the correct value. ") + getLocalizedText(question.help));
  }
}

function validateChooseField(erad, question, value) {
}

function validateAvailableDateField(erad, question, value, fieldSetAndValues) {
  const accessRightsPair = fieldSetAndValues.find(function(fieldSetAndValue) {
    return fieldSetAndValue.fieldSet.question.qid === 'grdm-file:access-rights';
  })
  if (!accessRightsPair) return;
  const requiredDateAccessRights = ['embargoed access'];
  if (requiredDateAccessRights.includes(accessRightsPair.value) && !value) {
    throw new Error(_("This field can't be blank."));
  }
}

function validateContactManagerField(erad, question, value, fieldSetAndValues) {
  function getFieldValue(qid) {
    const field = fieldSetAndValues.find(function(fieldSetAndValue) {
      return fieldSetAndValue.fieldSet.question.qid === qid;
    });
    if (!field) return null;
    return field.value;
  }

  const email = value;
  const tel = getFieldValue('grdm-file:data-man-tel');
  const address = getFieldValue('grdm-file:data-man-address-ja') &&
    getFieldValue('grdm-file:data-man-address-en');
  const org = getFieldValue('grdm-file:data-man-org-ja') &&
    getFieldValue('grdm-file:data-man-org-en');

  if (!email && !(tel && address && org)) {
    throw new Error(_("Contacts of data manager can't be blank. Please fill mail address, or organization name, address and phone number."));
  }
}

function validateCreators(erad, question, value) {
  const creators = JSON.parse(value);
  if (!creators) {
    return;
  }
  if (creators.some(function(creator) {
    return ! /^[0-9a-zA-Z]*$/.test(creator.number || '');
  })) {
    throw new Error(_("Please enter the correct value. ") + getLocalizedText(question.help));
  }
}

function createChooser(question, options) {
  const select = $('<select></select>');
  const defaultOption = $('<option></option>').attr('value', '');
  if (options.multiple) {
    defaultOption.text(_('(Not Modified)'));
    defaultOption.attr('selected', true)
  } else {
    defaultOption.text(_('Choose...'));
  }
  select.append(defaultOption);
  var groupElem = null;
  (question.options || []).forEach(function(opt) {
    if (opt.text && opt.text.startsWith('group:None:')) {
      groupElem = null;
    } else if (opt.text && opt.text.startsWith('group:')) {
      groupElem = $('<optgroup></optgroup>').attr('label', getLocalizedText(opt.tooltip));
      select.append(groupElem);
    } else {
      const optElem = $('<option></option>')
        .attr('value', opt.text === undefined ? opt : opt.text)
        .text(opt.text === undefined ? opt : getLocalizedText(opt.tooltip));
      if (!options.multiple && opt.default) {
        optElem.attr('selected', true);
      }
      if (groupElem) {
        groupElem.append(optElem);
      } else {
        select.append(optElem);
      }
    }
  });
  return select;
}

function normalize(value) {
  return value.replace(/\s+/g, ' ').trim();
}

function createFormElement(createHandler, question, options) {
  return {
    create: function(addToContainer, onChange) {
      const self = this;
      const elem = createHandler();
      if (options && options.readonly) {
        elem.attr('readonly', true);
      }
      if (onChange) {
        elem.change(function(event) {
          const value = event.target.value
          if (value && question.space_normalization) {
            const normalized = normalize(value);
            if (value !== normalized) {
              self.setValue(elem, normalized);
            }
          }
          onChange(event, options);
        });
      }
      elem.addClass('form-control');
      addToContainer(elem);
      return elem;
    },
    getValue: function(input) {
      return input.val();
    },
    setValue: function(input, value) {
      if (input.hasClass('datepicker')) {
        input.datepicker('update', value);
      } else {
        input.val(value);
      }
    },
    reset: function(input) {
      input.val(null);
    },
    disable: function(input, disabled) {
      input.attr('disabled', disabled);
    },
  };
}

function createClearFormElement(question) {
  return {
    create: function() {
      const clearId = 'clear-' + question.qid.replace(':', '-');
      const clearField = $('<input></input>')
        .addClass('form-check-input')
        .addClass('metadata-form-clear-checkbox')
        .attr('type', 'checkbox')
        .attr('id', clearId);
      const clearLabel = $('<label></label>')
        .addClass('form-check-label')
        .attr('for', clearId)
        .text(_('Clear'));
      const clearForm = $('<div></div>')
        .addClass('form-check')
        .append(clearField)
        .append(clearLabel);
      return {
        element: clearForm,
        checked: function() {
          return clearField.prop('checked');
        }
      };
    }
  };
}


function SingleElementField(formField, clearField, question, defaultValue, options, onChange) {
  if (!question.qid) {
    throw new Error('No labels');
  }
  const self = this;

  self.formField = formField;
  self.label = question.qid;
  self.title = question.title;
  self.help = question.help;
  self.defaultValue = defaultValue;
  self.clearField = null;

  self.createFormGroup = function(input, errorContainer) {
    const header = $('<div></div>');
    const label = $('<label></label>').text(self.getDisplayText());
    if (question.required) {
      label.append($('<span></span>')
        .css('color', 'red')
        .css('font-weight', 'bold')
        .text('*'));
    }
    header.append(label);
    if (clearField) {
      self.clearField = clearField.create();
      self.clearField.element.css('float', 'right');
      self.clearField.element.on('change', function() {
        if (self.clearField.checked()) {
          self.formField.reset(input);
          self.formField.disable(input, true);
        } else {
          self.formField.disable(input, false);
        }
      });
      header.append(self.clearField.element);
    }
    const group = $('<div></div>').addClass('form-group')
      .append(header);
    if (self.help) {
      var isDisplayedHelp = false;
      const helpLink = $('<a></a>')
          .addClass('help-toggle-button')
          .text(_('Show example'));
      const helpLinkBlock = $('<p></p>').append(helpLink);
      const help = $('<p></p>')
        .addClass('help-block')
        .text(self.getHelpText())
        .hide();
      helpLink.on('click', function(e) {
        e.preventDefault();
        if (isDisplayedHelp) {
          helpLink.text(_('Show example'));
          help.hide();
          isDisplayedHelp = false;
        } else {
          helpLink.text(_('Hide example'));
          help.show();
          isDisplayedHelp = true;
        }
      });
      group.append(helpLinkBlock).append(help);
    }
    group
      .append(input)
      .append(errorContainer);
    return group;
  }

  self.getDisplayText = function() {
    if (!self.title) {
      return self.label;
    }
    return getLocalizedText(self.title);
  }

  self.getHelpText = function() {
    return getLocalizedText(self.help);
  }

  self.getValue = function(input) {
    return formField.getValue(input);
  };

  self.setValue = function(input, value) {
    formField.setValue(input, value);
  };

  self.checkedClear = function() {
    return self.clearField && self.clearField.checked();
  };

  self.addElementTo = function(parent, errorContainer) {
    const input = formField.create(
      function(child) {
        parent.append(self.createFormGroup(child, errorContainer));
      },
      onChange
    );
    if (self.defaultValue) {
      formField.setValue(input, self.defaultValue);
    }
    return input;
  };
}


function createFileCapacityFieldElement(createHandler, options) {
  // ref: website/project/util.py sizeof_fmt()
  function sizeofFormat(num) {
    const units = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'];
    for (var i = 0; i < units.length; i ++) {
      const unit = units[i];
      if (Math.abs(num) < 1000) {
        return Math.round(num * 10) / 10 + unit + 'B';
      }
      num /= 1000.0
    }
    return Math.round(num * 10) / 10 + 'YB';
  }

  function calcCapacity(input, calcIndicator, errorContainer) {
    if (contextVars.file) {
      return new Promise(function (resolve, reject) {
        const totalSize = contextVars.file.size || 0;
        console.log(logPrefix, 'totalSize: ', totalSize);
        input.val(sizeofFormat(totalSize)).change();
        resolve();
      });
    }
    errorContainer.hide().text('');
    calcIndicator.show();
    options.wbcache.clearCache();
    const task = options.filepath.endsWith('/') ?
      options.wbcache.listFiles(options.filepath, true)
        .then(function (files) {
          return files.reduce(function(y, x) {
            return y + Number(x.item.attributes.size);
          }, 0);
        }) :
      new Promise(function (resolve, reject) {
        try {
          options.wbcache.searchFile(options.filepath, function (item) {
            resolve(Number(item.attributes.size));
          });
        } catch (err) {
          reject(err);
        }
      });
    return task
      .then(function (totalSize) {
        console.log(logPrefix, 'totalSize: ', totalSize);
        input.val(sizeofFormat(totalSize)).change();
      })
      .catch(function (err) {
        console.error(err);
        $osf.growl('Error', _('Could not list files') + ': ' + err.toString());
        Raven.captureMessage(_('Could not list files'), {
          extra: {
            error: err.toString()
          }
        });
        errorContainer.text(_('Could not list files')).show();
      })
      .then(function () {
        calcIndicator.hide();
      });
  }

  return {
    create: function(addToContainer, onChange) {
      const input = createHandler();
      if (options && options.readonly) {
        input.attr('readonly', true);
      }
      if (onChange) {
        input.change(function(event) {
          onChange(event, options);
        });
      }
      input.addClass('form-control');
      const container = $('<div>').append(input);
      if (!options || (!options.readonly && !options.multiple)) {
        container.css('display', 'flex');
        const calcIndicator = $('<i class="fa fa-spinner fa-pulse">')
          .hide();
        const calcButton = $('<a class="btn btn-default btn-sm">')
          .append($('<i class="fa fa-refresh"></i>'))
          .append($('<span></span>').text(_('Calculate')))
          .append(calcIndicator);
        const errorContainer = $('<span>')
          .css('color', 'red').hide();
        const calcContainer = $('<div>')
          .css('margin', 'auto 0 auto 8px')
          .append(calcButton)
          .append(errorContainer);
        var calculating = false;
        calcButton.on('click', function (e) {
          e.preventDefault();
          if (!calculating) {
            calculating = true;
            calcButton.attr('disabled', true);
            calcCapacity(input, calcIndicator, errorContainer)
              .then(function () {
                calculating = false;
                calcButton.attr('disabled', false);
              });
          }
        });
        container.append(calcContainer)
      }

      addToContainer(container);
      return container;
    },
    getValue: function(container) {
      return container.find('input').val();
    },
    setValue: function(container, value) {
      container.find('input').val(value);
    },
    reset: function(container) {
      container.find('input').val(null);
    },
    disable: function(container, disabled) {
      container.find('input').attr('disabled', disabled);
    },
  };
}

function createFileURLFieldElement(createHandler, options) {
  return {
    create: function(addToContainer, onChange) {
      const input = createHandler();
      if (options && options.readonly) {
        input.attr('readonly', true);
      }
      if (onChange) {
        input.change(function(event) {
          onChange(event, options);
        });
      }
      input.addClass('form-control');
      const container = $('<div>').append(input);
      if (!options || (!options.readonly && !options.multiple)) {
        container.css('display', 'flex');
        const fillButton = $('<a class="btn btn-default btn-sm">')
          .append($('<i class="fa fa-refresh"></i>'))
          .append($('<span></span>').text(_('Fill')));
        const fillContainer = $('<div>')
          .css('margin', 'auto 0 auto 8px')
          .append(fillButton);
        fillButton.on('click', function (e) {
          e.preventDefault();
          input.val(fangorn.getPersistentLinkFor(options.fileitem)).change();
        });
        container.append(fillContainer)
      }
      addToContainer(container);
      return container;
    },
    getValue: function(container) {
      return container.find('input').val();
    },
    setValue: function(container, value) {
      container.find('input').val(value);
    },
    reset: function(container) {
      container.find('input').val(null);
    },
    disable: function(container, disabled) {
      container.find('input').attr('disabled', disabled);
    },
  };
}

function createDataNoFieldElement(createHandler, fileMetadataSuggestion, question, options) {
  return {
    create: function(addToContainer, onChange) {
      const input = createHandler();
      if (options && options.readonly) {
        input.attr('readonly', true);
      }
      if (onChange) {
        input.change(function(event) {
          onChange(event, options);
        });
      }
      input.addClass('form-control');
      const container = $('<div>').append(input);
      if (!options || (!options.readonly && !options.multiple)) {
        container.css('display', 'flex');
        const calcIndicator = $('<i class="fa fa-spinner fa-pulse">')
          .hide();
        const fillButton = $('<a class="btn btn-default btn-sm">')
          .append($('<i class="fa fa-refresh"></i>'))
          .append($('<span></span>').text(_('Fill')))
          .append(calcIndicator);
        const errorContainer = $('<span>')
          .css('color', 'red').hide();
        const fillContainer = $('<div>')
          .css('margin', 'auto 0 auto 8px')
          .append(fillButton)
          .append(errorContainer);
        var calculating = false;
        fillButton.on('click', function (e) {
          e.preventDefault();
          if (!calculating) {
            calculating = true;
            fillButton.attr('disabled', true);
            errorContainer.hide().text('');
            calcIndicator.show();
            generateDataNo(fileMetadataSuggestion, options.fileitem)
              .then(function (value) {
                input.val(value).change();
              })
              .catch(function (err) {
                console.error(err);
                errorContainer.text(_('Could not generate Data No.')).show();
              })
              .then(function () {
                calculating = false;
                fillButton.attr('disabled', false);
                calcIndicator.hide();
              });
          }
        });
        container.append(fillContainer)
      }
      addToContainer(container);
      return container;
    },
    getValue: function(container) {
      return container.find('input').val();
    },
    setValue: function(container, value) {
      container.find('input').val(value);
    },
    reset: function(container) {
      container.find('input').val(null);
    },
    disable: function(container, disabled) {
      container.find('input').attr('disabled', disabled);
    },
  };
}

function createFileCreatorsFieldElement(erad, options) {
  const emptyLine = $('<td></td>')
    .attr('colspan', '4')
    .css('text-align', 'center')
    .css('padding', '1em')
    .text(_('No members'))
    .show();

  const addResearcher = function(container, defaultValues) {
    const numberInput = $('<input class="form-control" name="file-creator-number">');
    const nameJaInput = $('<input class="form-control" name="file-creator-name-ja">');
    const nameEnInput = $('<input class="form-control" name="file-creator-name-en">');
    if (options && options.readonly) {
      numberInput.attr('readonly', true);
      nameJaInput.attr('readonly', true);
      nameEnInput.attr('readonly', true);
    }
    if (defaultValues) {
      numberInput.val(defaultValues.number).change();
      nameJaInput.val(defaultValues.name_ja).change();
      nameEnInput.val(defaultValues.name_en).change();
    }
    const tr = $('<tr>')
      .append($('<td>').append(numberInput))
      .append($('<td>').append(nameJaInput))
      .append($('<td>').append(nameEnInput));
    if (!options || !options.readonly) {
      tr.append('<td><span class="file-creator-remove"><i class="fa fa-times fa-2x remove-or-reject"></i></span></td>');
    }
    const tbody = container.find('tbody');
    tbody.append(tr);
    numberInput.typeahead(
      {
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
              $osf.htmlEscape(data.kenkyusha_no) + ' - ' +
              $osf.htmlEscape(data.kenkyukikan_mei) + ' - ' +
              $osf.htmlEscape(data.kadai_mei) + ' (' + data.nendo + ')'
              + '</small></span></div>';
          }
        },
        source: substringMatcher(erad.candidates),
      }
    );
    numberInput.bind('typeahead:selected', function(event, data) {
      if (!data.kenkyusha_no) {
        return;
      }
      const names = data.kenkyusha_shimei.split('|');
      const jaNames = names.slice(0, Math.floor(names.length / 2))
      const enNames = names.slice(Math.floor(names.length / 2))
      nameJaInput.val(jaNames.join('')).change();
      nameEnInput.val(enNames.reverse().join(' ')).change();
    });
    tbody.find('.twitter-typeahead').css('width', '100%');
    emptyLine.hide();
  }

  return {
    create: function(addToContainer, onChange) {
      const thead = $('<thead>')
        .append($('<tr>')
          .append($('<th>' + _('e-Rad Researcher Number') + '</th>'))
          .append($('<th>' + _('Name (Japanese)') + '</th>'))
          .append($('<th>' + _('Name (English)') + '</th>'))
          .append($('<th></th>'))
        );
      const tbody = $('<tbody>');
      const container = $('<div></div>')
        .addClass('file-creators-container')
        .append($('<table class="table responsive-table responsive-table-xxs">')
          .append(thead)
          .append(tbody)
        );
      tbody.append(emptyLine);
      if (!options || !options.readonly) {
        const addButton = $('<a class="btn btn-success btn-sm">')
          .append($('<i class="fa fa-plus"></i>'))
          .append($('<span></span>').text(_('Add')));
        container.append(addButton);
        addButton.on('click', function (e) {
          e.preventDefault();
          addResearcher(container);
        });
        tbody.on('click', '.file-creator-remove', function (e) {
          e.preventDefault();
          $(this).closest('tr').remove();
          if (container.find('tbody tr').length === 0) {
            emptyLine.show();
          }
          if (onChange) {
            onChange(e, options);
          }
        });
      }
      tbody.on('change', 'input', function (e) {
        const value = e.target.value
        if (value && e.target.getAttribute('name').startsWith('file-creator-name')) {
          const normalized = normalize(value);
          if (value !== normalized) {
            e.target.value = normalized;
          }
        }
        if (onChange) {
          onChange(e, options);
        }
      });
      addToContainer(container);
      return container;
    },
    getValue: function(container) {
      const researchers = container.find('tbody tr').map(function () {
        return {
          'number': $(this).find('[name=file-creator-number]').val(),
          'name_ja': $(this).find('[name=file-creator-name-ja]').val(),
          'name_en': $(this).find('[name=file-creator-name-en]').val()
        };
      }).toArray().filter(function (researcher) {
        return Object.values(researcher).some(function (v) { return v && v.trim().length > 0; });
      });
      if (researchers.length === 0) {
        return '';
      }
      return JSON.stringify(researchers);
    },
    setValue: function(container, value) {
      const researchers = value ? JSON.parse(value) : [];
      researchers.forEach(function (researcher) {
        addResearcher(container, researcher);
      });
    },
    reset: function(container) {
      container.find('tbody').empty();
    },
    disable: function(container, disabled) {
      const btn = container.find('.btn');
      if (disabled) {
        btn.addClass('disabled');
      } else {
        btn.removeClass('disabled');
      }
    },
  };
}

function createERadResearcherNumberFieldElement(erad, options) {
  return {
    create: function(addToContainer, onChange) {
      const input = $('<input></input>').addClass('erad-researcher-number');
      if (options && options.readonly) {
        input.attr('readonly', true);
      }
      const container = $('<div></div>')
        .addClass('erad-researcher-number-container')
        .append(input.addClass('form-control'));
      addToContainer(container);
      input.typeahead(
        {
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
                $osf.htmlEscape(data.kenkyusha_no) + ' - ' +
                $osf.htmlEscape(data.kenkyukikan_mei) + ' - ' +
                $osf.htmlEscape(data.kadai_mei) + ' (' + data.nendo + ')'
                + '</small></span></div>';
            }
          },
          source: substringMatcher(erad.candidates),
        }
      );
      input.bind('typeahead:selected', function(event, data) {
        if (data.kenkyusha_shimei) {
          const names = data.kenkyusha_shimei.split('|');
          const jaNames = names.slice(0, Math.floor(names.length / 2))
          const enNames = names.slice(Math.floor(names.length / 2))
          $('.e-rad-researcher-name-ja').val(jaNames.join('')).change();
          $('.e-rad-researcher-name-en').val(enNames.reverse().join(' ')).change();
        }
        if (data.kenkyukikan_mei) {
          const names = data.kenkyukikan_mei.split('|');
          const jaNames = names.slice(0, Math.floor(names.length / 2))
          const enNames = names.slice(Math.floor(names.length / 2))
          $('.file-institution-ja').typeahead('val', jaNames.join('')).change();
          $('.file-institution-en').typeahead('val', enNames.join(' ')).change();
        }
      });
      container.find('.twitter-typeahead').css('width', '100%');
      if (onChange) {
        input.change(function(event) {
          onChange(event, options);
        });
      }
      return container;
    },
    getValue: function(container) {
      return container.find('input').val();
    },
    setValue: function(container, value) {
      container.find('input').val(value);
    },
    reset: function(container) {
      container.find('input').val(null);
    },
    disable: function(container, disabled) {
      container.find('input').attr('disabled', disabled);
    },
  };
}


function createFileInstitutionFieldElement(options, format) {
  return {
    create: function(addToContainer, onChange) {
      const input = $('<input></input>').addClass(format);
      if (options && options.readonly) {
        input.attr('readonly', true);
      }
      const container = $('<div></div>')
        .addClass('erad-file-institution')
        .append(input.addClass('form-control'));
      addToContainer(container);
      function getJaName(data) {
        if (data && data.labels && data.labels.length) {
          const ja = data.labels.filter(function(label) {
            return label.iso639 === 'ja';
          });
          if (ja.length) {
            return ja[0].label;
          }
        }
        return null;
      }
      input.typeahead(
        {
          hint: false,
          highlight: true,
          minLength: 0
        },
        {
          display: function(data) {
            const ja = getJaName(data);
            if (format.endsWith('ja') && ja) {
              return ja;
            }
            return data.name;
          },
          templates: {
            suggestion: function(data) {
              const ja = getJaName(data);
              return '<div style="background-color: white;"><span>' + $osf.htmlEscape(data.name) + '</span> ' +
                '<span><small class="m-l-md text-muted">'+
                (ja ? $osf.htmlEscape(ja) : '')
                + '</small></span></div>';
            }
          },
          source: $osf.throttle(function (q, cb) {
            $.ajax({
              method: 'GET',
              url: 'https://api.ror.org/organizations',
              data: {
                query: q
              },
              cache: true,
            }).then(function(result) {
              cb(result && result.items || []);
            }).catch(function(error) {
              console.error(error);
              cb([]);
            });
          }, 500, {leading: false}),
        }
      );
      input.bind('typeahead:selected', function(event, data) {
        const en = data.name;
        const ja = getJaName(data) || en;
        const id = data.id;
        $('.file-institution-en').typeahead('val', en).change();
        $('.file-institution-ja').typeahead('val', ja).change();
        $('.file-institution-identifier').val(id).change();
      });
      container.find('.twitter-typeahead').css('width', '100%');
      if (onChange) {
        input.change(function(event) {
          onChange(event, options);
        });
      }
      return container;
    },
    getValue: function(container) {
      return container.find('input').val();
    },
    setValue: function(container, value) {
      container.find('input').val(value);
    },
    reset: function(container) {
      container.find('input').val(null);
    },
    disable: function(container, disabled) {
      container.find('input').attr('disabled', disabled);
    },
  };
}


function substringMatcher(candidates) {
  return function findMatches(q, cb) {
    const substrRegex = new RegExp(q, 'i');
    const matches = (candidates || []).filter(function(c) {
      if (!c.kenkyusha_no) {
        return false;
      }
      return substrRegex.test(c.kenkyusha_no);
    });
    cb(matches);
  };
}

function generateDataNo(fileMetadataSuggestion, fileitem) {
  const itemUrl = fangorn.getPersistentLinkFor(fileitem);
  const filepath = itemUrl.substr(itemUrl.indexOf('files/'));
  const format = 'data_format_number';
  return fileMetadataSuggestion.suggest(filepath, format)
    .then(function (suggestions) {
      return (suggestions.find(function (s) { return s.format === format}) || {}).value;
    });
}

module.exports = {
  createField: createField,
  validateField: validateField
};
