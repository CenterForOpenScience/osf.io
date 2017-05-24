'use strict';

var $ = require('jquery');
var bootbox = require('bootbox');
var Raven = require('raven-js');
var $osf = require('js/osfHelpers.js');
var getConfirmationCode = require('js/projectSettings.js').getConfirmationCode;

$(document).ready(function() {

  //Project overview >> Component Widget >> Event/Click handler for componentQuickActions menu item: Delete.
  $('.deleteComponent').each( function() {
    $(this).off().on('click', function(e) {
      var componentIndex = $(this).data('index');
      var component = window.contextVars.nodes[componentIndex].node;

      if(component.childExists){
        $osf.growl(
          'Error',
          'Any child components must be deleted prior to deleting this component.',
          'danger',
          30000
        );
      }else{
        getConfirmationCode(
          component.node_type,
          component.isPreprint,
          component.api_url
        );
      }
    });
  });

});
