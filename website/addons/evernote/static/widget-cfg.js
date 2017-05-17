'use strict';

require('./evernote.css');
require('datatables.net-dt/css/jquery.dataTables.css');
require('datatables-select/dist/css/select.dataTables.min.css');
//require('datatables-select/dist/css/select.dataTables.css');

var $ = require('jquery');
// http://stackoverflow.com/a/34255097/7782 --> why datatables.net and not datatables-dt
var dt = require( 'datatables.net' )();
var dts = require('datatables-select')();
var ko = require('knockout');
var $osf = require('js/osfHelpers');


var EvernoteWidget = function(urls) {

    self = this;
    self.urls = urls;

    self.notes = ko.observableArray();

    // subscribe to changes in notes?
    self.notes.subscribe(function(changes) {
      //console.log(changes);


      //var notes = self.notes();
      var notes = $.map(self.notes(),  function(o){
        return {
          title: o['title'],
          guid: o['guid'],
          created: new $osf.FormattableDate(o['created']).local,
          updated: new $osf.FormattableDate(o['updated']).local
        }
      });

      self.notes_dt = $('#evernote-notes-list').DataTable( {
        responsive: true,
        select: {
           style: 'single'
        },
        "lengthMenu": [ 5, 10, 25, 50],
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

       var row = self.notes_dt.row( this );

       $("#evernote-notedisplay").html("<i>Loading note...</i>");
       // display title and note body
       $('#evernote-note-title').html(
          row.data()['title']
        );
       self.displayNote(row.id());

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


// Skip if widget is not correctly configured
if ($('#evernoteWidget').length) {
  var settingsUrl = window.contextVars.node.urls.api + 'evernote/settings/';

  var settings = $.getJSON(settingsUrl);

  settings.done(function(data) {

    var urls = data.result.urls;
    var ew = new EvernoteWidget(urls);
    $osf.applyBindings(ew, '#evernoteWidget');

  });

  settings.fail(function(){
    console.log(arguments);
  });
}
