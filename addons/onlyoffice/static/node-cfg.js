'use strict';

var $ = require('jquery');
var m = require('mithril');
var ko = require('knockout');
var Raven = require('raven-js');
var osfHelpers = require('js/osfHelpers');
var ChangeMessageMixin = require('js/changeMessage');
var SaveManager = require('js/saveManager');

var SHORT_NAME = 'onlyoffice';
var logPrefix = '[' + SHORT_NAME + '] ';


function NodeSettings() {
  var self = this;

  ChangeMessageMixin.call(self);
}

$.extend(NodeSettings.prototype, ChangeMessageMixin.prototype);

var settings = new NodeSettings();
osfHelpers.applyBindings(settings, '#' + SHORT_NAME + 'Scope');
