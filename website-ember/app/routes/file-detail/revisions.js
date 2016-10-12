import Ember from 'ember';

export default Ember.Route.extend({
    model() {
        const file = this.modelFor('file-detail').file;
        return file.query('versions', {'page[size]': 100});
    },
});
