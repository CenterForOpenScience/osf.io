var connect = require('connect'),
    sharejs = require('share').server;

var server = connect(connect.logger());

var options = {
    db: {type: 'none'},
    browserChannel: { cors: "http://localhost:5000" }
}; // See docs for options.

// Attach the sharejs REST and Socket.io interfaces to the server
sharejs.attach(server, options);

server.listen(7007, function() {
    console.log('Server running at http://127.0.0.1:7007/');
});