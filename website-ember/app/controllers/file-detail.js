import Ember from 'ember';
import config from 'ember-get-config';

import CommentableMixin from 'ember-osf/mixins/commentable';
import TaggableMixin from 'ember-osf/mixins/taggable-mixin';

export default Ember.Controller.extend(CommentableMixin, TaggableMixin, {
    fileManager: Ember.inject.service(),
    session: Ember.inject.service(),

    checkedIn: Ember.computed.none('model.checkout'),
    canCheckIn: Ember.computed('model.checkout',
                               'session.data.authenticated.id', function() {
        let checkoutID = this.get('model.checkout');
        let userID = this.get('session.data.authenticated.id');
        return checkoutID === userID;
    }),
    canEdit: Ember.computed.or('checkedIn', 'canCheckIn'),

    actions: {
        fileDetail(file) {
            this.transitionToRoute('nodes.detail.files.provider.file',
                                   this.get('node'),
                                   file.get('provider'),
                                   file);
        },

        nodeDetail(node) {
            this.transitionToRoute('nodes.detail', node);
        },

        delete() {
            let file = this.get('model');
            this.get('fileManager').deleteFile(file).then(() => {
                window.location.replace(config.OSF.url + 'project/' + file.get('node').get('id') + '/files/');
            });
        },

        checkOut() {
            let file = this.get('model');
            this.get('fileManager').checkOut(file);
        },

        checkIn() {
            let file = this.get('model');
            this.get('fileManager').checkIn(file);
        },
    }
});
