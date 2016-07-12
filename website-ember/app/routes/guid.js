import Ember from 'ember';

export default Ember.Route.extend({
    model() {
        return this.store.findRecord('file', '5783db51f69cacf2b35a58d4');
    },
    setupController(controller, model) {
        this._super(controller, model);
        let node = this.store.findRecord('node', '4cnkv');
        // let node = this.modelFor('nodes.detail');
        controller.set('node', node);
    },
});
