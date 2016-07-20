import Ember from 'ember';

/** Borrowed from here https://gist.github.com/ViktorQvarfordt/10432265 - will need to be modified.
*/
export default Ember.Component.extend({
    didInsertElement: function() {
        this.editor = window.ace.edit(this.get('element'));
        this.get('initializeAce')(this.editor);
        this.editor.on('change', function() {
            this.set('value', this.editor.getSession().getValue());
        }.bind(this));
    },
    valueChanged: function () {
        if (!this.get('value')) {
            this.editor.getSession().setValue('');
        } else if (this.editor.getSession().getValue() !== this.get('value')) {
            this.editor.getSession().setValue(this.get('value'));
        }
    }.observes('value')
});
