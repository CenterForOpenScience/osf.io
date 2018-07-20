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

$(document).ready(function() {
   var collectedTypeItems = JSON.parse($('#id_collected_type_choices').val());
   collectedTypeItems.forEach(function(element){
       $('#tags-input-collected-types').tagsinput('add', element)
   });

   var statusItems = JSON.parse($('#id_status_choices').val());
   statusItems.forEach(function(element){
       $('#tags-input-status').tagsinput('add', element)
   });
});