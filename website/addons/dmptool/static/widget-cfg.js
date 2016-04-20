'use strict';

require('./dmptool.css');

var $ = require('jquery');
var ko = require('knockout');
var $osf = require('js/osfHelpers');


var DmptoolWidget = function(urls) {

    self = this;
    self.urls = urls;

    self.init();

 }

 DmptoolWidget.prototype.init = function() {
    console.log("");


 };


// Skip if widget is not correctly configured
if ($('#dmptoolWidget').length) {
  var settingsUrl = window.contextVars.node.urls.api + 'dmptool/settings/';

  var settings = $.getJSON(settingsUrl);

  settings.done(function(data) {

    var urls = data.result.urls;
    var ew = new DmptoolWidget(urls);
    $osf.applyBindings(ew, '#dmptoolWidget');

  });

  settings.fail(function(){
    console.log(arguments);
  });
}
