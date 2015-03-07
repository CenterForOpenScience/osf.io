'use strict';
var assign = require('object-assign');
var sinon = window.sinon || require('sinon');

/**
 * Utility to create a fake server with sinon.
 *
 * See http://sinonjs.org/docs/#fakeServer
 *
 * Example:
 *
 * var server;
 * before(() => {
 *     server = createServer({
 *        '/projects/': {
 *              method: 'GET',
 *              response: {'id': '12345'},
 *         }
 *        '/projects/': {
 *              method: 'POST',
 *              response: {message: 'Successfully created project.},
 *              status: 201
 *         }
 *     })
 * });
 *
 * after(() => { server.restore(); });
 */
var defaultHeaders = {'Content-Type': 'application/json'};
function createServer(endpoints) {
    var server = sinon.fakeServer.create();
    for (var url in endpoints) {
        var endpoint = endpoints[url];
        var headers = assign(
            {},
            defaultHeaders,
            endpoints.headers
        );
        server.respondWith(
            endpoint.method || 'GET',
            url,
            [
                endpoint.status || 200,
                headers,
                JSON.stringify(endpoint.response)
            ]
        );
    }
    return server;
}

module.exports = {
    createServer: createServer
};
