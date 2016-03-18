'use strict';
var $ = require('jquery');

var SaveManager = function(url, method, opts) {
    var self = this;
    self.url = url;
    self.method = method || 'PUT';
    opts = opts || {};
    self.xhrOpts = $.extend({}, {
        contentType: 'application/json',
        dataType: 'json'
    }, opts.xhrOpts || {});
    self.dirty = opts.dirty || function(){return false;};
    var warn = opts.warn || true;

    self.queued = null;

    self.blocking = null;
    if (warn) {
        $(window).on('beforeunload', function() {
            if (self.blocking || self.dirty())  {
                return 'You have unsaved changes.';
            }
        });
    }
};
SaveManager.prototype.enqueue = function(opts, promise) {
    var self = this;
    if (self.queued) {
        self.queued = self.dequeue.bind(self, opts, promise);
    }
    else {
        self.queued = function() {
            return self.dequeue(opts, promise);
        };
    }
    return promise.promise();
};
SaveManager.prototype.dequeue = function(opts, promise) {
    var self = this;
    self.blocking = $.ajax(opts)
        .always(function() {
            if (self.queued) {
                self.blocking = self.queued(); // resolves self.queuePromise
                self.queued = null;
            }
            else {
                self.blocking = null;
            }
        })
        .done(promise.resolve)
        .fail(promise.reject);
    return self.blocking;
};
SaveManager.prototype.save = function(data) {
    var self = this;
    var promise = $.Deferred();
    var opts = $.extend({}, {
        url: self.url,
        method: self.method,
        data: typeof data !== 'string' ? JSON.stringify(data): data
    }, self.xhrOpts || {});

    if (!self.blocking) {
        return self.dequeue(opts, promise);
    }
    else {
        return self.enqueue(opts, promise);
    }
};

module.exports = SaveManager;
