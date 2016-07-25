import Ember from 'ember';

export function permissionMap(params/*, hash*/) {
    var map = {
        read: 'Read',
        write: 'Read + Write',
        admin: 'Administrator'
    };
    var permission = params[0];
    return map[permission];
}

export default Ember.Helper.helper(permissionMap);
