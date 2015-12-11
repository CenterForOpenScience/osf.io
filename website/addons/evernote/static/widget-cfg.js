'use strict';

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

var EvernoteWidget = function(urls) {

    self = this;

    console.log(urls);

    self.notes = ko.observableArray();
    self.fetchNotes = $.getJSON.bind(null, urls.notes, function(notes) {
       self.notes(notes);
    });

    self.init();

 }

 EvernoteWidget.prototype.init = function() {
    this.fetchNotes();
 };

 EvernoteWidget.prototype.openEditDialog = function (note, event) {
   $("#evernote-notedisplay")[0].value = note.title;
 }

// Skip if widget is not correctly configured
if ($('#evernoteWidget').length) {
  var settingsUrl = window.contextVars.node.urls.api + 'evernote/settings/';

  $.getJSON( settingsUrl,  function( data ) {
     console.log(data.result.urls.notes);
     var urls = data.result.urls;
     var ew = new EvernoteWidget(urls);
     $osf.applyBindings(ew, '#evernoteWidget');

     // apply tooltip to all btn-evernote
     $(".btn-evernote").tooltip()
  });
}
