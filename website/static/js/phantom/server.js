/**
 * Created by kushagragupta on 4/22/15.
 */
var express = require('express');
var phantom = require('phantom');
var spectre = require('commander');

spectre
    .version('0.1.0')
    .option('-c, --cache', 'Cache files to disk', false)
    .option('-p, --port [port]', 'Port to listen on', parseInt, 9090)
    .option('-h, --host [host]', 'The host to mirror', 'localhost:5000')
    .option('-t, --timeout [millis]', 'The max amount of time to wait for a page to finish loading in milliseconds', parseInt, 5000)
    .parse(process.argv);

var app = express();
var ignoredPaths = ['favicon.ico', '^/static/.+'];
var ignoreRegex = new RegExp(ignoredPaths.map(function(reg) { return '(' + reg + ')';}).join('|'));

var phantomParams = {
    parameters: {
        'load-images': false,
        'disk-cache': !!spectre.cache,
        'local-to-remote-url-access': true
    }
};

function doCallback(page, callback) {
    page.get('content', function(content) {
        page.get('pageStatusCode', function(status) {
            page.close();
            callback(status || 200, content);
        });
    });
}

function setTimeout(page, time) {
    page.evaluate(function(timeout) {
        setTimeout(window.callPhantom.bind('spectre.TimeOut'), timeout);
    }, undefined, spectre.timeout);
}

function getRenderedHtml(url, callback, page) {
    page.set('onLoadFinished', setTimeout.bind(this, page, spectre.timeout));

    page.set('onResourceReceived', function(res) {
        if (res.status > 299 && res.status < 400) return;
        page.set('onResourceReceived', null);
        page.set('pageStatusCode', res.status);
    });

    page.set('onCallback', function(command, wait) {
        if(command === 'spectre.Wait') {
            page.set('spectreWaiting', true);
            if (!!wait) setTimeout(page, wait);
        } else if(command === 'spectre.Done') {
            doCallback(page, callback);
        } else if(command === 'spectre.TimeOut') {
            page.get('spectreWaiting', function(waiting) {
                if (!!!waiting) doCallback(page, callback);
            });
        }
    });

    console.log('requesting url ' + url);
    page.open(url, function(status) {
        if (status === 'failed') {
            console.log('failed to fetch url ' + url);
            callback(500, '');
        }
    });
}

console.log('Spinning up phantomjs instance...');
phantom.create(phantomParams, function(ph) {
//    app.get('*', function(req, resp) {
//        var url = 'http://' + spectre.host + req.url;
//
//        if (req.url.match(ignoreRegex) !== null) {
//            console.log('Redirecting requested resource ' + req.url);
//            return resp.redirect(url);
//        }
//
//        ph.createPage(getRenderedHtml.bind(this, url, function(status, body) {
//            resp.status(status).send(body);
//        }));

            ph.createPage(function(page) {
                page.onCallback = function (data) {
                    console.log('CALLBACK: ' + JSON.stringify(data));
                };

            });

    console.log('Starting server; listening on port ' + spectre.port + '...');
    app.listen(spectre.port);
});