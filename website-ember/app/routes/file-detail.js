import Ember from 'ember';
import AuthenticatedRouteMixin from 'ember-simple-auth/mixins/authenticated-route-mixin';

export default Ember.Route.extend(AuthenticatedRouteMixin, {
    fileManager: Ember.inject.service(),
    // TODO Find a better way to load node.  Node needs to be loaded before file-browser component renders.
    model(params) {
        return Ember.RSVP.hash({
            file: this.store.findRecord('file', params.guid),
            node: this.store.findRecord('file', params.guid).then(function (file) {
                return file.get('node');
            })
        });

    },
    actions: {
        download(versionID) {
            let file = this.modelFor(this.routeName).file;
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
