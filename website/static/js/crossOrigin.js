var xhook = require('../vendor/bower_components/xhook/dist/xhook.js').xhook;
var URI = require('URIjs');
var jquery = require('jquery');

var xdrExists = navigator.appVersion.indexOf('MSIE 9.') !== -1;

// Adapted from http://jpillora.com/xhook/example/ie-8-9-cors-polyfill.html
xhook.before(function(request, callback) {
  // Skip modern browsers
  if (!xdrExists) {
    return callback();
  }
  // Skip same-origin requests
  var url = request.url;
  var loc = window.location;
  var hostname = loc.hostname + (loc.port ? ':' + loc.port : '');
  if (!/^https?:\/\/([^\?\/]+)/.test(url) || RegExp.$1 === hostname) {
    return callback();
  }
  // Method must be GET or POST; if neither, pass override in query
  var method = request.method;
  if (method.toUpperCase() !== 'GET') {
    url = URI(request.url)
      .addSearch({method: request.method.toUpperCase()})
      .toString();
    method = 'POST';
  }
  // Request must use same protocol as current location
  url = url.replace(/^https?:/,loc.protocol);
  var xdr = new window.XDomainRequest();
  xdr.timeout = request.timeout;
  // Attach proxy events
  var proxy = function(e) {
    xdr['on' + e] = function() {
      request.xhr.dispatchEvent(e);
    };
  };
  var events = ['progress', 'timeout', 'error'];
  for (var i=0; i<events.length; i++) {
    proxy(events[i]);
  }
  xdr.onload = function() {
    callback({
      status: 200,
      statusText: 'OK',
      headers: {
        'Content-Type': xdr.contentType
      },
      text: xdr.responseText
    });
  };
  xdr.open(method, url);
  xdr.send(request.body);
});

// Must tell jQuery that CORS is available, else requests won't be sent
jquery.support.cors = true;

// Hack: Disable xhook if not using MSIE
if (!xdrExists) {
    xhook.disable();
}
