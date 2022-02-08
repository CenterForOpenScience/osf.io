'use strict';

var $ = require('jquery');
var $osf = require('js/osfHelpers');
require('typeahead.js');


function BaseTextField(label) {
  if (!label) {
    throw new Error('No labels');
  }
  var self = this;

  self.label = label;

  self.createFormGroup = function(input) {
    var label = $('<label></label>').text(self.label);
    var group = $('<div></div>').addClass('form-group')
      .append(label)
      .append(input);
    return group;
  }

  self.addElementTo = function(parent) {
    var input = $('<input></input>');
    input.addClass('form-control');
    parent.append(self.createFormGroup(input));
    return input;
  };
}


function ERadResearcherNumberField(erad, label) {
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
        /*if ( $.isFunction( settings.complete ) ) {
            settings.complete( event, data.value );
        }*/
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
}


module.exports = {
  ERadResearcherNumberField: ERadResearcherNumberField,
  ERadResearcherNameField: ERadResearcherNameField,
};
