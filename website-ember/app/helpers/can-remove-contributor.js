import Ember from 'ember';

export function canRemoveContributor(params/*, hash*/) {
    var contributor = params[0];
    var currentUser = params[1];
    var registration = params[2];
    var currentUserId = currentUser.get('currentUserId');
    return contributor.id.split('-')[1] === currentUserId && !registration;
}

export default Ember.Helper.helper(canRemoveContributor);
