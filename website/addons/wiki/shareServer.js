// Library imports
var sharejs = require('share');
var livedb = require('livedb');
var Duplex = require('stream').Duplex;
var WebSocketServer = require('ws').Server;
var express = require('express');
var http = require('http');
var async = require('async');

// Server Options
var host = process.env.SHAREJS_SERVER_HOST || 'localhost';
var port = process.env.SHAREJS_SERVER_PORT || 7007;

// Mongo options
var dbHost = process.env.SHAREJS_DB_HOST || 'localhost';
var dbPort = process.env.SHAREJS_DB_PORT || 27017;
var dbName = process.env.SHAREJS_DB_NAME || 'sharejs';

// Server setup
var mongo = require('livedb-mongo')(
    'mongodb://' + dbHost + ':' + dbPort + '/' + dbName,
    {safe:true}
);
var backend = livedb.client(mongo);
var share = sharejs.server.createClient({backend: backend});
var app = express();
var server = http.createServer(app);
var wss = new WebSocketServer({ server: server});

// Local variables
var docs = {};  // TODO: Should this be stored in mongo?
var locked = {};

// Allow CORS
app.use(function(req, res, next) {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    next();
});

// Serve static sharejs files
app.use(express.static(sharejs.scriptsDir));

// Broadcasts message to all clients connected to that doc
// TODO: Can we access the relevant list without iterating over every client?
wss.broadcast = function(docId, message) {
    console.log('Broadcasting ' + message + ' to all clients on ' + docId);
    async.each(this.clients, function (client, cb) {
        if (client.userMeta && client.userMeta.docId === docId) {
            try {
                client.send(message);
            } catch (e) {
                // ignore errors - connection will likely be closed by library
            }
        }

        cb();
    });
};

wss.on('connection', function(client) {
    var stream = new Duplex({objectMode: true});

    stream._read = function() {};
    stream._write = function(chunk, encoding, callback) {
        if (client.state !== 'closed') {
            try {
                client.send(JSON.stringify(chunk));
            } catch (e) {
                // ignore errors - connection will likely be closed by library
            }
        }
        callback();
    };

    stream.headers = client.upgradeReq.headers;
    stream.remoteAddress = client.upgradeReq.connection.remoteAddress;

    client.on('message', function(data) {
        if (client.userMeta && locked[client.userMeta.docId]) {
            wss.broadcast(client.userMeta.docId, JSON.stringify({type: 'lock'}));
            return;
        }

        try {
            data = JSON.parse(data);
        } catch (e) {
            console.error('could not parse message data as json');
            return;
        }

        // Handle our custom messages separately
        if (data.registration) {
            console.log('Client registered: ' + data);
            var docId = data.docId;
            var userId = data.userId;

            // Create a metadata entry for this document
            if (!docs[docId]) {
                docs[docId] = {};
            }

            // Add user to metadata
            if (!docs[docId][userId]) {
                docs[docId][userId] = {
                    name: data.userName,
                    url: data.userUrl,
                    count: 1,
                    gravatar: data.userGravatar
                };
            } else {
                docs[docId][userId].count++;
            }

            // Attach metadata to the client object
            client.userMeta = data;
            wss.broadcast(docId, JSON.stringify({type: 'meta', users: docs[docId]}));

            // Lock client if doc is locked
            if (locked[docId]) {
                try {
                    client.send(JSON.stringify({type: 'lock'}));
                } catch (e) {
                    // ignore errors - connection will likely be closed by library
                }
            }
        } else {
            stream.push(data);
        }
    });

    client.on('close', function(reason) {
        console.log('Client disconnected: ' + reason);
        if (client.userMeta) {
            var docId = client.userMeta.docId;
            var userId = client.userMeta.userId;

            if (docs[docId] && docs[docId][userId]) {
                docs[docId][userId].count--;
                if (docs[docId][userId].count === 0) {
                    delete docs[docId][userId];

                    if (!Object.keys(docs[docId]).length) {
                        delete docs[docId];
                    }
                }
            }

            wss.broadcast(docId, JSON.stringify({type: 'meta', users: docs[docId]}));
        }

        stream.push(null);
        stream.emit('close');
    });

    stream.on('error', function(msg) {
        console.error(msg);
        client.close(msg);
    });

    stream.on('end', function() {
        client.close();
    });

    // Give the stream to sharejs
    return share.listen(stream);
});

// Lock a document
app.post('/lock/:id', function (req, res, next) {
    locked[req.params.id] = true;
    wss.broadcast(req.params.id, JSON.stringify({type: 'lock'}));
    console.log(req.params.id + ' was locked.');
    res.send(req.params.id + ' was locked.');
});

// Unlock a document
app.post('/unlock/:id', function (req, res, next) {
    delete locked[req.params.id];
    wss.broadcast(req.params.id, JSON.stringify({type: 'unlock'}));
    console.log(req.params.id + ' was unlocked.');
    res.send(req.params.id + ' was unlocked.');
});

// Redirect from a document
app.post('/redirect/:id/:redirect', function (req, res, next) {
    wss.broadcast(req.params.id, JSON.stringify({
        type: 'redirect',
        redirect: req.params.redirect
    }));
    console.log(req.params.id + ' was redirected to ' + req.params.redirect);
    res.send(req.params.id + ' was redirected to ' + req.params.redirect);
});

// Redirect from a deleted document
app.post('/delete/:id/:redirect', function (req, res, next) {
    wss.broadcast(req.params.id, JSON.stringify({
        type: 'delete',
        redirect: req.params.redirect
    }));
    console.log(req.params.id + ' was deleted and redirected to ' + req.params.redirect);
    res.send(req.params.id + ' was deleted and redirected to ' + req.params.redirect);
});

server.listen(port, host, function() {
    console.log('Server running at http://' + host + ':' + port);
});