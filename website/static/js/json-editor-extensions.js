var $ = require('jquery');

var jedit = require('json-editor'); // TODO webpackify


JSONEditor.defaults.editors.commentableString = JSONEditor.defaults.editors.string.extend({
    build: function() {
        this._super();

        $(this.input).after($('<span>Comments go here</span>'));
    }
});
