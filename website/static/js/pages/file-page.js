var $ = require('jquery');
var m = require('mithril');
var $osf = require('js/osfHelpers');
var FileViewPage = require('js/filepage');
var waterbutler = require('js/waterbutler');
require('../../css/pages/wiki-page.css'); // We need wiki css here because it uses the same Editor syntax. Need to refactor


m.mount(document.getElementsByClassName('file-view-panels')[0], FileViewPage(window.contextVars));
