'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var ko = require('knockout');
var $osf = require('js/osfHelpers.js');
var ProjectSettings = require('js/projectSettings.js');

$(document).ready(function() {
  $(".deleteComponent").each( function() {
    $(this).off().on('click', function(e) {
        var component = $(this).data('summary');
        if(component.childExists){
            $osf.growl('Error', 'Any child components must be deleted prior to deleting this project.','danger', 30000);
        }else{
            ProjectSettings.getConfirmationCode(component.node_type, component.isPreprint, component.api_url);
        }
     });
   });

});
