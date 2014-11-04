var express = require('express'),
    sharejs = require('share-6-fork').server;

var server = express();
var docs = {};

var options = {
    db: {type: 'mongo'},
    browserChannel: { cors: "http://localhost:5000" },
    auth: function(agent, action) {
        agent.name = agent.authentication;
        if (action.type === 'connect') {
//            console.log(agent);
        }
        action.accept();
    }
};

// Attach the sharejs REST and Socket.io interfaces to the server
session = sharejs.attach(server, options, function(session) {
    session.on('close', function() {
        console.log('client closed');
    })
});

// Allow CORS
server.all('*', function(req, res, next) {
    res.header("Access-Control-Allow-Origin", "*");
    res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
    next();
});

// Add user
server.post('/add/:uuid/:name', function addUser(req, res, next) {
    var uuid = req.params.uuid;
    var name = req.params.name;

    if (!docs[uuid])
        docs[uuid] = {};
    docs[uuid][name] = docs[uuid][name] ? docs[uuid][name] + 1 : 1;

    res.send(docs[uuid]);
});

// Remove user
server.post('/remove/:uuid/:name', function removeUser(req, res, next) {
    var uuid = req.params.uuid;
    var name = req.params.name;

    if (docs[uuid]) {
        docs[uuid][name] = docs[uuid][name] ? docs[uuid][name] - 1 : 0;
        if (docs[uuid][name] === 0) {
            delete docs[uuid][name];
            if (!Object.keys(docs[uuid]).length){}
                delete docs[uuid];
        }
    }

    res.send(docs[uuid]);
});

// Get list of docs/users as JSON
server.get('/users', function getUsers(req, res, next) {
    res.send(docs);
});

server.listen(7007, function() {
    console.log('Server running at http://127.0.0.1:7007/');
});