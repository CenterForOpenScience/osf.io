'use strict';

require('./evernote.css');
require('datatables.net-dt/css/jquery.dataTables.css');

var $ = require('jquery');
// http://stackoverflow.com/a/34255097/7782 --> why datatables.net and not datatables-dt
var dt = require( 'datatables.net' )();
require('datatables-select');
var ko = require('knockout');
var $osf = require('js/osfHelpers');

//var moment = require('moment');


var EvernoteWidget = function(urls) {

    self = this;
    self.urls = urls;

    self.notes = ko.observableArray();

    // subscribe to changes in notes?
    self.notes.subscribe(function(changes) {
      //console.log(changes);


      var notes = self.notes();

      self.notes_dt = $('#evernote-notes-list').DataTable( {
        responsive: true,
        data: notes,
        rowId: 'guid',
        columns: [
            { data: "title", title: "title" },
            { data: "created" , title: "created"},
            { data: "updated" , title: "updated"},
        ]

       } );

    }, null, "arrayChange");

    // on selecting a row -- I think there should be a better way
    $('#evernote-notes-list').on( 'click', 'tr', function () {
       console.log( 'Row id: '+self.notes_dt.row( this ).id() );
       $("#evernote-notedisplay").html("<b>Loading note...</b>");
       self.displayNote(self.notes_dt.row( this ).id());
    } );

    self.fetchNotes = $.getJSON.bind(null, urls.notes, function(notes) {
       self.notes(notes);
    });

    self.init();

 }

 EvernoteWidget.prototype.init = function() {
    this.fetchNotes();
    console.log("fetchNotes done: notes: " + self.notes());


 };

 EvernoteWidget.prototype.displayNote = function (note_guid) {


   // make ajax call to note to retrieve some basic info about note
   // ultimately, rendered html

   var note = $.getJSON(this.urls.note + note_guid +"/");

   note.done(function(data) {
     $("#evernote-notedisplay").html(data.html);
   });

 };


 // EvernoteWidget.prototype.openEditDialog = function (note, event) {
 //
 //
 //   // make ajax call to note to retrieve some basic info about note
 //   // ultimately, rendered html
 //
 //   var note = $.getJSON(this.urls.note + note.guid +"/");
 //
 //   note.done(function(data) {
 //     $("#evernote-notedisplay").html(data.html);
 //   });
 //
 // };

// Skip if widget is not correctly configured
if ($('#evernoteWidget').length) {
  var settingsUrl = window.contextVars.node.urls.api + 'evernote/settings/';

  var settings = $.getJSON(settingsUrl);

  settings.done(function(data) {

    var urls = data.result.urls;
    var ew = new EvernoteWidget(urls);
    $osf.applyBindings(ew, '#evernoteWidget');

    // apply tooltip to all btn-evernote
    $(".btn-evernote").tooltip();

  });

  settings.fail(function(){
    console.log(arguments);
  });
}
