// Configuration options
var port = 7007;
var dbHost = 'localhost';
var dbPort = 27017;
var dbName = 'sharejstest';

// Library imports
var sharejs = require('share');
var livedb = require('livedb');
var Duplex = require('stream').Duplex;
var browserChannel = require('browserchannel').server;
var express = require('express');

// Server setup
var mongo = require('livedb-mongo')(
    'mongodb://' + dbHost + ':' + dbPort + '/' + dbName,
    {safe:true}
);
var backend = livedb.client(mongo);
var share = sharejs.server.createClient({backend: backend});
var server = express();

// Local variables
var docs = {};
var numClients = 0;
var bcOptions = {
    sessionTimeoutInterval: 5000,  // max ms before disconnect is registered
    cors: 'http://localhost:5000'  // only necessary for http requests
};

// Allow CORS
server.all('*', function(req, res, next) {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    next();
});

// Serve static sharejs files
server.use(express.static(sharejs.scriptsDir));

// OT and user tracking server
server.use(browserChannel(bcOptions, function(client) {

    var stream = new Duplex({objectMode: true});

    stream._read = function() {};
    stream._write = function(chunk, encoding, callback) {
        if (client.state !== 'closed') {
            client.send(chunk);
        }
        callback();
    };

    client.on('open', function(data) {
        console.log('opened', data);
    });

    client.on('message', function(data) {
        // Handle our custom messages separately
        if (data.registration) {
            var docId = data.docId;
            var userId = data.userId;

            if (!docs[docId])
                docs[docId] = {};

            if (!docs[docId][userId]) {
                docs[docId][userId] = {
                    name: data.userName,
                    url: data.userUrl,
                    count: 1
                }
            } else {
                docs[docId][userId].count++;
            }
            numClients += 1;
            client.userMeta = data; // Attach metadata to the client object
            console.log('new user:', data.userName, '| Total:', numClients);
        } else {
            stream.push(data);
        }
    });

    // Called several seconds after the socket is closed
    client.on('close', function(reason) {
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

        numClients -= 1;
        console.log('rem user:', client.userMeta.userName, '| Total:', numClients);

        stream.push(null);
        stream.emit('close');
    });

    stream.on('end', function() {
        client.close();
    });

    // Give the stream to sharejs
    return share.listen(stream);

}));

// Get list of docs/users as JSON
server.get('/users', function getUsers(req, res, next) {
    res.send(docs);
});

server.listen(port, function() {
    console.log('Server running at http://127.0.0.1:' + port);
});