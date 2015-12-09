'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

var EvernoteWidget = function(urls) {

    self = this;

    console.log(urls);

    self.hello_var = ko.observable("Happy Wednesday");
    self.notes = ko.observableArray();
    $.getJSON(urls.notes, function (data) {
      self.notes(data)
    })

 }

// Skip if widget is not correctly configured
if ($('#evernoteWidget').length) {
  var settingsUrl = window.contextVars.node.urls.api + 'evernote/settings/';
  console.log(settingsUrl);
  $.getJSON( settingsUrl,  function( data ) {
     console.log(data.result.urls.notes);
     var urls = data.result.urls;
     var ew = new EvernoteWidget(urls);
     $osf.applyBindings(ew, '#evernoteWidget');
  });
}
