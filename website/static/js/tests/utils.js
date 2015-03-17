'use strict';
var $ = require('jquery');
// var sinon = window.sinon || require('sinon');

/**
 * Utility to create a fake server with sinon.
 *
 * Sets server.autoRespond = true, so that the server responds
 * automatically after every request.
 * Also assumes that responses will be JSON by default, so
 * no need to JSON.stringify your response.
 *
 *
 * See http://sinonjs.org/docs/#fakeServer
 *
 * Example:
 *
 * var server;
 * before(() => {
 *     server = createServer(sinon, [
 *        {url: '/projects/':  method: 'GET', response: {'id': '12345'}}
 *        {url: '/projects/': method: 'POST',
 *          response: {message: 'Successfully created project.'}, status: 201}
 *        {url: /\/project\/(\d+)/, method: 'GET',
 *          response: {message: 'Got single project.'}}
 *     ]);
 * });
 *
 * after(() => { server.restore(); });
 */
var defaultHeaders = {'Content-Type': 'application/json'};
function createServer(sinon, endpoints) {
    var server = sinon.fakeServer.create();
    endpoints.forEach(function(endpoint) {
        var headers = $.extend(
            {},
            defaultHeaders,
            endpoints.headers
        );
        server.respondWith(
            endpoint.method || 'GET',
            endpoint.url,
            [
                endpoint.status || 200,
                headers,
                JSON.stringify(endpoint.response)
            ]
        );
    });
    server.autoRespond = true;
    return server;
}

module.exports = {
    createServer: createServer
};
