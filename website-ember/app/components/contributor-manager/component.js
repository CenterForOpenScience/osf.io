import Ember from 'ember';

export default Ember.Component.extend({
    permissionChanges: {},
    bibliographicChanges: {},
    actions: {
        permissionChange(contributor, permission) {
            this.set(`permissionChanges.${contributor.id}`, permission.toLowerCase());
        },
        bibliographicChange(contributor, isBibliographic) {
            this.set(`bibliographicChanges.${contributor.id}`, isBibliographic);
        },
    }
});
