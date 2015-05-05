var express = require('express');
var phantom = require('phantom');
var app = express();

app.get('/', function (req, res) {

    var url = req.query.url;
    console.log(url);
    console.log(req.query);


    phantom.create(function(ph){

       ph.createPage(function (page) {

           page.open(url, function (status) {
               if (status == 'success') {
                   console.log("Success");

                   page.evaluate(
                       function () {
                           return document.documentElement.outerHTML;
                       },
                       function (content) {
//                             console.log(content);
                           res.send(content);
                           console.log('RESPONSE SEND');
                           ph.exit();
                       });
               }
               else {
                   console.log("Status Failed");
                   ph.exit();
               }
           })
       });
    });

});

var server = app.listen(3000, function () {

  var host = server.address().address;
  var port = server.address().port;

  console.log('Example app listening at http://%s:%s', host, port);

});