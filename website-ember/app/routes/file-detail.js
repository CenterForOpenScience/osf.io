import Ember from 'ember';
import AuthenticatedRouteMixin from 'ember-simple-auth/mixins/authenticated-route-mixin';

export default Ember.Route.extend(AuthenticatedRouteMixin, {
    fileManager: Ember.inject.service(),
    model() {
        return this.store.findRecord('file', '5786614263ca2ff0887a202b');
    },
    setupController(controller, model) {
        this._super(controller, model);
        let node = this.store.findRecord('node', '4cnkv');
        // let node = this.modelFor('nodes.detail');
        controller.set('node', node);
    },
    actions: {
        download(versionID) {
            let file = this.modelFor(this.routeName);
            let options = {};
            if (typeof versionID !== 'undefined') {
                options.query = {
                    version: versionID
                };
            }
            let url = this.get('fileManager').getDownloadUrl(file, options);
            window.open(url);
        }
    }
});
