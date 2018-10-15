require('bootstrap-tagsinput');
require('bootstrap-tagsinput/dist/bootstrap-tagsinput.css');

$('#tags-input-collected-types').on('itemAdded', function(event) {
    $('#id_collected_type_choices').val(JSON.stringify($('#tags-input-collected-types').tagsinput('items')));
});

$('#tags-input-collected-types').on('itemRemoved', function(event) {
    $('#id_collected_type_choices').val(JSON.stringify($('#tags-input-collected-types').tagsinput('items')));
});

$('#tags-input-status').on('itemAdded', function(event) {
    $('#id_status_choices').val(JSON.stringify($('#tags-input-status').tagsinput('items')));
});

$('#tags-input-status').on('itemRemoved', function(event) {
    $('#id_status_choices').val(JSON.stringify($('#tags-input-status').tagsinput('items')));
});

$('#tags-input-issue').on('itemAdded', function(event) {
    $('#id_issue_choices').val(JSON.stringify($('#tags-input-issue').tagsinput('items')));
});

$('#tags-input-issue').on('itemRemoved', function(event) {
    $('#id_issue_choices').val(JSON.stringify($('#tags-input-issue').tagsinput('items')));
});

$('#tags-input-volume').on('itemAdded', function(event) {
    $('#id_volume_choices').val(JSON.stringify($('#tags-input-volume').tagsinput('items')));
});

$('#tags-input-volume').on('itemRemoved', function(event) {
    $('#id_volume_choices').val(JSON.stringify($('#tags-input-volume').tagsinput('items')));
});

$('#tags-input-program-area').on('itemAdded', function(event) {
    $('#id_program_area_choices').val(JSON.stringify($('#tags-input-program-area').tagsinput('items')));
});

$('#tags-input-program-area').on('itemRemoved', function(event) {
    $('#id_program_area_choices').val(JSON.stringify($('#tags-input-program-area').tagsinput('items')));
});

$(document).ready(function() {
   var collectedTypeItems = JSON.parse($('#id_collected_type_choices').val());
   collectedTypeItems.forEach(function(element){
       $('#tags-input-collected-types').tagsinput('add', element)
   });

   var statusItems = JSON.parse($('#id_status_choices').val());
   statusItems.forEach(function(element){
       $('#tags-input-status').tagsinput('add', element)
   });

   var issueItems = JSON.parse($('#id_issue_choices').val());
   issueItems.forEach(function(element){
       $('#tags-input-issue').tagsinput('add', element)
   });

   var volumeItems = JSON.parse($('#id_volume_choices').val());
   volumeItems.forEach(function(element){
       $('#tags-input-volume').tagsinput('add', element)
   });

   var programAreaItems = JSON.parse($('#id_program_area_choices').val());
   programAreaItems.forEach(function(element){
       $('#tags-input-program-area').tagsinput('add', element)
   });
});
