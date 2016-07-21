import { moduleForComponent, test } from 'ember-qunit';
import hbs from 'htmlbars-inline-precompile';

moduleForComponent('contributor-manager', 'Integration | Component | contributor manager', {
  integration: true
});

test('it renders', function(assert) {
  // Set any properties with this.set('myProperty', 'value');
  // Handle any actions with this.on('myAction', function(val) { ... });

  this.render(hbs`{{contributor-manager}}`);

  assert.equal(this.$().text().trim(), '');

  // Template block usage:
  this.render(hbs`
    {{#contributor-manager}}
      template block text
    {{/contributor-manager}}
  `);

  assert.equal(this.$().text().trim(), 'template block text');
});
