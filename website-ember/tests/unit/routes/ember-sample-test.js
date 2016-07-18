import { moduleFor, test } from 'ember-qunit';

moduleFor('route:ember-sample', 'Unit | Route | ember sample', {
    // Specify the other units that are required for this test.
    // needs: ['controller:foo']
});

test('it exists', function(assert) {
    let route = this.subject();
    assert.ok(route);
});
