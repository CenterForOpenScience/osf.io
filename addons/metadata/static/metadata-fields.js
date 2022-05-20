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

function createField(erad, question, valueEntry, options, callback) {
  if (question.type == 'string') {
    return createStringField(erad, question, (valueEntry || {}).value, options, callback);
  }
  if (question.type == 'choose') {
    return createChooseField(erad, question, (valueEntry || {}).value, options, callback);
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

function createStringField(erad, question, value, options, callback) {
  if (question.format == 'text') {
    return new SingleElementField(
      createFormElement(function() {
        return $('<input></input>');
      }, options),
      question,
      value,
      options,
      callback
    );
  } else if (question.format == 'textarea') {
    return new SingleElementField(
      createFormElement(function() {
        return $('<textarea></textarea>');
      }, options),
      question,
      value,
      options,
      callback
    );
  } else if (question.format == 'date') {
    return new SingleElementField(
      createFormElement(function() {
        const elem = $('<input></input>').addClass('datepicker');
        datepicker.mount(elem, null);
        return elem;
      }, options),
      question,
      value,
      options,
      callback
    );
  } else if (question.format == 'file-creators') {
    return new SingleElementField(
      createFileCreatorsFieldElement(erad, options),
      question,
      value,
      options,
      callback
    );
  } else if (question.format == 'e-rad-researcher-number') {
    return new SingleElementField(
      createERadResearcherNumberFieldElement(erad, options),
      question,
      value,
      options,
      callback
    );
  } else if (
    question.format == 'e-rad-researcher-name-ja' ||
    question.format == 'e-rad-researcher-name-en'
  ) {
    return new SingleElementField(
      createFormElement(function() {
        return $('<input></input>').addClass(question.format);
      }, options),
      question,
      value,
      options,
      callback
    );
  } else if (question.format == 'file-capacity') {
    return new SingleElementField(
      createFileCapacityFieldElement(function() {
        return $('<input></input>');
      }, options),
      question,
      value,
      options,
      callback
    );
  } else if (question.format == 'file-url') {
    return new SingleElementField(
      createFileURLFieldElement(function() {
        return $('<input></input>');
      }, options),
      question,
      value,
      options,
      callback
    );
  }
  return new SingleElementField(
    createFormElement(function() {
      return $('<input></input>');
    }, options),
    question,
    value,
    options,
    callback
  );
}

function createChooseField(erad, question, value, options, callback) {
  if (question.format == 'singleselect') {
    return new SingleElementField(
      createFormElement(function() {
        return createChooser(question.options);
      }, options),
      question,
      value,
      options,
      callback
    );
  }
  return new SingleElementField(
    createFormElement(function() {
      return $('<input></input>');
    }, options),
    question,
    value,
    options,
    callback
  );
}

function validateStringField(erad, question, value) {
}

function validateChooseField(erad, question, value) {
}

function createChooser(options) {
  const select = $('<select></select>');
  select.append($('<option></option>').attr('value', '').text(_('Choose...')));
  (options || []).forEach(function(opt) {
    if (opt.text === undefined) {
      const optElem = $('<option></option>').attr('value', opt).text(opt);
      select.append(optElem);
      return;
    }
    const optElem = $('<option></option>').attr('value', opt.text).text(getLocalizedText(opt.tooltip));
    select.append(optElem);
  });
  return select;
}

function createFormElement(createHandler, options) {
  return {
    create: function(addToContainer, callback) {
      const elem = createHandler();
      if (options && options.readonly) {
        elem.attr('readonly', true);
      }
      if (callback) {
        elem.change(callback);
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
  };
}


function SingleElementField(formField, question, defaultValue, options, callback) {
  if (!question.qid) {
    throw new Error('No labels');
  }
  const self = this;

  self.formField = formField;
  self.label = question.qid;
  self.title = question.title;
  self.defaultValue = defaultValue;

  self.createFormGroup = function(input, errorContainer) {
    const label = $('<label></label>').text(self.getDisplayText());
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

  self.getDisplayText = function() {
    if (!self.title) {
      return self.label;
    }
    return getLocalizedText(self.title);
  }

  self.getValue = function(input) {
    return formField.getValue(input);
  };

  self.setValue = function(input, value) {
    formField.setValue(input, value);
  };

  self.addElementTo = function(parent, errorContainer) {
    const input = formField.create(
      function(child) {
        parent.append(self.createFormGroup(child, errorContainer));
      },
      callback
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
        input.val(sizeofFormat(totalSize));
      })
      .catch(function (err) {
        console.error(err);
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
    create: function(addToContainer, callback) {
      const input = createHandler();
      if (options && options.readonly) {
        input.attr('readonly', true);
      }
      if (callback) {
        input.change(callback);
      }
      input.addClass('form-control');
      const container = $('<div>').css('display', 'flex').append(input);
      if (!options || !options.readonly) {
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
  };
}

function createFileURLFieldElement(createHandler, options) {
  return {
    create: function(addToContainer, callback) {
      const input = createHandler();
      if (options && options.readonly) {
        input.attr('readonly', true);
      }
      if (callback) {
        input.change(callback);
      }
      input.addClass('form-control');
      const container = $('<div>').css('display', 'flex').append(input);
      if (!options || !options.readonly) {
        const fillButton = $('<a class="btn btn-default btn-sm">')
          .append($('<i class="fa fa-refresh"></i>'))
          .append($('<span></span>').text(_('Fill')));
        const fillContainer = $('<div>')
          .css('margin', 'auto 0 auto 8px')
          .append(fillButton);
        fillButton.on('click', function (e) {
          e.preventDefault();
          input.val(fangorn.getPersistentLinkFor(options.fileitem));
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
  };
}

function createFileCreatorsFieldElement(erad, options) {
  const typeaheadSource = (function () {
    const allResearchers = erad.candidates.map(function (c) {
      return {
        kenkyusha_no: c.kenkyusha_no,
        kenkyusha_shimei: c.kenkyusha_shimei
      };
    });
    const uniqResearchers = {};
    allResearchers.forEach(function (researcher) {
      uniqResearchers[JSON.stringify(researcher)] = researcher;
    });
    return substringMatcher(Object.values(uniqResearchers));
  })();
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
      numberInput.val(defaultValues.number);
      nameJaInput.val(defaultValues.name_ja);
      nameEnInput.val(defaultValues.name_en);
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
              $osf.htmlEscape(data.kenkyusha_no) + ' ' +
              $osf.htmlEscape(data.kenkyusha_shimei) +
              + '</small></span></div>';
          }
        },
        source: typeaheadSource,
      }
    );
    numberInput.bind('typeahead:selected', function(event, data) {
      if (!data.kenkyusha_no) {
        return;
      }
      const names = data.kenkyusha_shimei.split('|');
      const jaNames = names.slice(0, Math.floor(names.length / 2))
      const enNames = names.slice(Math.floor(names.length / 2))
      nameJaInput.val(jaNames.join(' '));
      nameEnInput.val(enNames.join(' '));
    });
    tbody.find('.twitter-typeahead').css('width', '100%');
    emptyLine.hide();
  }

  return {
    create: function(addToContainer, callback) {
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
          if (callback) {
            callback();
          }
        });
      }
      tbody.on('change', '.input', function (e) {
        if (callback) {
          callback();
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
        return Object.values(researcher).every(function (v) { return v && v.trim().length > 0; });
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
    }
  };
}

function createERadResearcherNumberFieldElement(erad, options) {
  return {
    create: function(addToContainer, callback) {
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
                $osf.htmlEscape(data.kenkyukikan_mei) + ' - ' +
                $osf.htmlEscape(data.kadai_mei) + ' (' + data.nendo + ')'
                + '</small></span></div>';
            }
          },
          source: substringMatcher(erad.candidates),
        }
      );
      input.bind('typeahead:selected', function(event, data) {
        if (!data.kenkyusha_shimei) {
          return;
        }
        const names = data.kenkyusha_shimei.split('|');
        const jaNames = names.slice(0, Math.floor(names.length / 2))
        const enNames = names.slice(Math.floor(names.length / 2))
        $('.e-rad-researcher-name-ja').val(jaNames.join(' '));
        $('.e-rad-researcher-name-en').val(enNames.join(' '));
      });
      container.find('.twitter-typeahead').css('width', '100%');
      if (callback) {
        input.change(callback);
      }
      return container;
    },
    getValue: function(container) {
      return container.find('input').val();
    },
    setValue: function(container, value) {
      container.find('input').val(value);
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

module.exports = {
  createField: createField,
  validateField: validateField
};
