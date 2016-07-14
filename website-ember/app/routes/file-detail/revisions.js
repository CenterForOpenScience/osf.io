import Ember from 'ember';

export default Ember.Route.extend({
    model() {
        let file = this.modelFor('file-detail').file;
        return file.get('versions');
    },
});
