'use strict';

require('./evernote.css');

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('js/osfHelpers');


var EvernoteWidget = function(urls) {

    self = this;

    self.urls = urls;

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


   // make ajax call to note to retrieve some basic info about note
   // ultimately, rendered html

   var note = $.getJSON(this.urls.note + note.guid +"/");

   note.done(function(data) {
     $("#evernote-notedisplay").html(data.html);
   });

 };

// Skip if widget is not correctly configured
if ($('#evernoteWidget').length) {
  var settingsUrl = window.contextVars.node.urls.api + 'evernote/settings/';

  var settings = $.getJSON(settingsUrl);

  settings.done(function(data) {

    var urls = data.result.urls;
    var ew = new EvernoteWidget(urls);
    $osf.applyBindings(ew, '#evernoteWidget');

    // apply tooltip to all btn-evernote
    $(".btn-evernote").tooltip()

  });

  settings.fail(function(){
    console.log(arguments);
  });
}
