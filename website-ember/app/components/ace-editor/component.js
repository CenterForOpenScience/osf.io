import Ember from 'ember';

/** Borrowed from here https://gist.github.com/ViktorQvarfordt/10432265 - will need to be modified.
*/
export default Ember.Component.extend({
    fileManager: Ember.inject.service(),
    didInsertElement: function() {
        var _this = this;
        _this.editor = window.ace.edit(_this.get('element'));
        var file = _this.get('file');
        _this.get('fileManager').getContents(file).then(function(contents) {
            _this.set('value', contents);
        });
        _this.get('initializeAce')(this.editor);
        _this.editor.on('change', function() {
            _this.set('value', _this.editor.getSession().getValue());
        }.bind(_this));
    },
    valueChanged: function () {
        if (!this.get('value')) {
            this.editor.getSession().setValue('');
        } else if (this.editor.getSession().getValue() !== this.get('value')) {
            this.editor.getSession().setValue(this.get('value'));
        }
    }.observes('value'),

});
