import Ember from 'ember';

export default Ember.Route.extend({
    currentUser: Ember.inject.service(),

    model(params) {
        return this.store.findRecord('node', params.node_id);
    },

    setupController(controller) {
        this.get('currentUser').load()
            .then((user) => controller.set('user', user))
            .catch(() => controller.set('user', null));

        return this._super(...arguments);
    }
});
