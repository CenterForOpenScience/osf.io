import Ember from 'ember';
import config from 'ember-get-config';

import CommentableMixin from 'ember-osf/mixins/commentable';
import TaggableMixin from 'ember-osf/mixins/taggable-mixin';

export default Ember.Controller.extend(CommentableMixin, TaggableMixin, {
    fileManager: Ember.inject.service(),
    session: Ember.inject.service(),

    checkedIn: Ember.computed.none('model.file.checkout'),
    canCheckIn: Ember.computed('model.file.checkout',
                               'session.data.authenticated.id', function() {
        let checkoutID = this.get('model.file.checkout');
        let userID = this.get('session.data.authenticated.id');
        return checkoutID === userID;
    }),
    canEdit: Ember.computed.or('checkedIn', 'canCheckIn'),

    actions: {
        fileDetail(file) {
            this.transitionToRoute('file-detail', file.get('id'));
        },

        nodeDetail(node) {
            // TODO Test this.
            window.location.replace(config.OSF.url + node.id);
        },

        delete() {
            let file = this.get('model').file;
            let node = this.get('model').node;
            this.get('fileManager').deleteFile(file).then(() => {
                window.location.replace(config.OSF.url + 'project/' + node.get('id') + '/files/');
            });
        },

        checkOut() {
            let file = this.get('model').file;
            this.get('fileManager').checkOut(file);
        },

        checkIn() {
            let file = this.get('model').file;
            this.get('fileManager').checkIn(file);
        },
    }
});
