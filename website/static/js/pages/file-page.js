var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var FileViewPage = require('js/filepage');
var waterbutler = require('js/waterbutler');

m.mount(document.getElementsByClassName('file-view-panels')[0], FileViewPage(window.contextVars));
