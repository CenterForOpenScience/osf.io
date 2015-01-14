/**
 * Initialization code for the Wiki view page.
 */
'use strict';

var $osf = require('osfHelpers');
// Apply an empty ViewModel to the #wikiName element so that
// we can use the tooltip binding handler. =/
$osf.applyBindings({}, '#wikiName');
