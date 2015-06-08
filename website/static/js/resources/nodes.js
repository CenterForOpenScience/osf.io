'use strict';
/**
 * API client for the 'nodes' resource.
 *
 * Usage:
 *
 *    var client = new NodeClient();
 *    client.list({pageSize: 100}).then(function(nodes) {
 *        nodes.forEach(function(node) {
 *            console.log(node.title);
 *            console.log(node.description);
 *        })
 *    });
 *
 *    client.detail('abc12').then(function(node) {
 *        console.log('Information about Node abc12:');
 *        console.log(node.title);
 *        console.log(node.isPublic);
 *    });
 */
var base = require('js/resources/base');
var oop = require('js/oop');

/** Node model */
var Node = oop.defclass({
    /** Params is the data from the server. */
    constructor: function(params) {
        this.id = params.id;
        this.title = params.title;
        this.description = params.description;
        this.isPublic = params.is_public;
    },
    toString: function() {
        return '[Node ' + this.id + ']';
    }
});


var NodeClient = oop.extend(base.BaseClient, {
    /**
     * Return a promise that resolves to an Array of Node objects.
     * @param {object} params
     *  {number} pageSize
     */
    list: function(params) {
        params = params || {};
        var ret = $.Deferred();
        // TODO: page numbber, filtering etc.
        var query = params.pageSize != null ? 'page[size]=' + params.pageSize : '';
        this._request({url: '/nodes/',
                      query: query})
            .done(function(resp) {
                var nodes = $.map(resp.data, function(nodeData) {
                    return new Node(nodeData);
                });
                ret.resolve(nodes);
            }).fail(base.captureError('Could not fetch nodes list.'));
        return ret.promise();
    }
    // TODO: detail(nodeID)
});

module.exports = {
    Node: Node,
    NodeClient: NodeClient
};
