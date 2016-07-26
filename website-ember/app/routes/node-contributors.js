import Ember from 'ember';
import loadAll from 'ember-osf/utils/load-relationship';

export default Ember.Route.extend({
    currentUser: Ember.inject.service(),

    model(params) {
        return this.store.findRecord('node', params.node_id);
    },

    setupController(controller, model) {
        this.get('currentUser').load()
            .then((user) => controller.set('user', user))
            .catch(() => controller.set('user', null));

        // Fetch all contributors
        let dest = Ember.A();
        loadAll(model, 'contributors', dest).then(() =>
            // Ember doesn't like when two widgets both fetch data from the same endpoint (even with different query params)-
            // this results in one request being canceled
            controller.set('contributors', dest));

        return this._super(...arguments);
    }
});
