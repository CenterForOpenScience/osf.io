// Library imports
var util = require('util');
var http = require('http');
var raven = require('raven');
var sharejs = require('share');
var livedb = require('livedb');
var Duplex = require('stream').Duplex;
var WebSocketServer = require('ws').Server;
var express = require('express');
var bodyParser = require('body-parser');
var morgan = require('morgan');
var async = require('async');

var settings = {
    debug: process.env.SHAREJS_DEBUG ? process.env.SHAREJS_DEBUG === 'true' : true,
    // Server Options
    host: process.env.SHAREJS_SERVER_HOST || 'localhost',
    port: process.env.SHAREJS_SERVER_PORT || 7007,
    corsAllowOrigin: process.env.SHAREJS_CORS_ALLOW_ORIGIN || 'http://localhost:5000',
    // Mongo options
    dbHost: process.env.SHAREJS_DB_HOST || 'localhost',
    dbPort: process.env.SHAREJS_DB_PORT || 27017,
    dbName: process.env.SHAREJS_DB_NAME || 'sharejs',
    // Raven client
    sentryDSN: process.env.SHAREJS_SENTRY_DSN
};

var client = new raven.Client(settings.sentryDSN);

if (!settings.debug) {
    client.patchGlobal(function() {
        // It is highly discouraged to leave the process running after a
        // global uncaught exception has occurred.
        //
        // https://github.com/getsentry/raven-node#catching-global-errors
        // http://nodejs.org/api/process.html#process_event_uncaughtexception
        //
        console.log('Uncaught Exception process exiting');
        process.exit(1);
    });
}

// Server setup
var mongo = require('livedb-mongo')(
    util.format('mongodb://%s:%s/%s', settings.dbHost, settings.dbPort, settings.dbName),
    {safe:true}
);
var backend = livedb.client(mongo);
var share = sharejs.server.createClient({backend: backend});
var app = express();
var jsonParser = bodyParser.json();
var server = http.createServer(app);
var wss = new WebSocketServer({server: server});

// Local variables
var docs = {};  // TODO: Should this be stored in mongo?
var locked = {};

// Allow X-Forwarded-For headers
app.set('trust proxy');

// Raven Express Middleware
app.use(raven.middleware.express(settings.sentryDSN));
app.use(morgan('common'));

// Allow CORS
app.use(function(req, res, next) {
    res.header('Access-Control-Allow-Origin', settings.corsAllowOrigin);
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    next();
});

// Serve static sharejs files
app.use(express.static(sharejs.scriptsDir));

// Broadcasts message to all clients connected to that doc
// TODO: Can we access the relevant list without iterating over every client?
wss.broadcast = function(docId, message) {
    async.each(this.clients, function (client, cb) {
        if (client.userMeta && client.userMeta.docId === docId) {
            try {
                client.send(message);
            } catch (e) {
                // ignore errors - connection should be handled by share.js library
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
                // ignore errors - connection should be handled by share.js library
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
            client.captureMessage('Could not parse message data as json', {message: message});
            return;
        }

        // Handle our custom messages separately
        if (data.registration) {
            console.info('[User Registered] docId: %s, userId: %s', data.docId, data.userId);
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
                    // ignore errors - connection should be handled by share.js library
                }
            }
        } else {
            stream.push(data);
        }
    });

    client.on('close', function(reason) {
        if (client.userMeta) {
            console.info('[Connection Closed] docId: %s, userId: %s, reason: %s', client.userMeta.docId, client.userMeta.userId, reason);
        } else {
            console.info('[Connection Closed] reason: %s', reason);
        }

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
        client.captureMessage('Could not parse message data as json', {msg: msg});
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
    console.info('[Document Locked] docId: %s', req.params.id);
    res.send(util.format('%s was locked.', req.params.id));
});

// Unlock a document
app.post('/unlock/:id', jsonParser, function (req, res, next) {
    delete locked[req.params.id];
    wss.broadcast(req.params.id, JSON.stringify({
        type: 'unlock',
        contributors: req.body // Contributors with write permission
    }));
    console.info('[Document Unlocked] docId: %s', req.params.id);
    res.send(util.format('%s was unlocked.', req.params.id));
});

// Redirect from a document
app.post('/redirect/:id/:redirect', function (req, res, next) {
    wss.broadcast(req.params.id, JSON.stringify({
        type: 'redirect',
        redirect: req.params.redirect
    }));
    console.info('[Document Redirect] docId: %s, redirect: %s', req.params.id, req.params.redirect);
    res.send(util.format('%s was redirected to %s', req.params.id, req.params.redirect));
});

// Redirect from a deleted document
app.post('/delete/:id/:redirect', function (req, res, next) {
    wss.broadcast(req.params.id, JSON.stringify({
        type: 'delete',
        redirect: req.params.redirect
    }));
    console.info('[Document Delete] docId: %s, redirect: %s', req.params.id, req.params.redirect);
    res.send(util.format('%s was deleted and redirected to %s', req.params.id, req.params.redirect));
});

server.listen(settings.port, settings.host, function() {
    console.log('Server running at http://%s:%s', settings.host, settings.port);
});