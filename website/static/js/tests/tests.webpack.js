// Generate a single webpack bundle for all tests for faster testing
// See https://github.com/webpack/karma-webpack#alternative-usage

// Configure raven with a fake DSN to avoid errors in test output
var Raven = require('raven-js');
Raven.config('http://abc@example.com:80/2');

// Include all files that end with .test.js (core tests)
var context = require.context('.', true, /.*test\.js$/); //make sure you have your directory and regex test set correctly!
context.keys().forEach(context);

// Include all files in the addons directory that end with .test.js
var addonContext = require.context('../../../../addons/', true, /.*test\.js$/); //make sure you have your directory and regex test set correctly!
addonContext.keys().forEach(addonContext);
