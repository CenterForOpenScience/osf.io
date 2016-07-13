import Ember from 'ember';
import AuthenticatedRouteMixin from 'ember-simple-auth/mixins/authenticated-route-mixin';

export default Ember.Route.extend(AuthenticatedRouteMixin, {
    fileManager: Ember.inject.service(),
    model(params) {
        return this.store.findRecord('file', params.guid);
    },
    setupController(controller, model) {
        this._super(controller, model);
        let node = model.get('node');
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
