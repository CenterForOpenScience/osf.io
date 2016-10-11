import Ember from 'ember';

/** Adapted from here https://gist.github.com/ViktorQvarfordt/10432265
*/
export default Ember.Component.extend({
    fileManager: Ember.inject.service(),
    didInsertElement: function() {
        this.editor = window.ace.edit(this.get('element'));

        const file = this.get('file');

        this.get('fileManager')
            .getContents(file)
            .then(contents => this.set('value', contents));

        this.get('initializeAce')(this.editor);

        this.editor.on('change', () => this.set('value', this.editor.getSession().getValue()));
    },
    valueChanged: Ember.observer('value', function () {
        const session = this.editor.getSession();
        const value = this.get('value');

        if (!value) {
            session.setValue('');
        } else if (session.getValue() !== value) {
            session.setValue(value);
        }
    }),

});
