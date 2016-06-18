'use strict';

var viewModels = require('../apiPersonalToken');

var ctx = window.contextVars;
var apiPersonalToken = new viewModels.TokenDetail('#tokenDetail', ctx.urls);
