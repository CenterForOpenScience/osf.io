'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

var EvernoteWidget = function() {
    this.hello_var = "Happy Friday";
 }

// Skip if widget is not correctly configured
if ($('#evernoteWidget').length) {
  var ew = new EvernoteWidget();
  $osf.applyBindings(ew, '#evernoteWidget');
}
