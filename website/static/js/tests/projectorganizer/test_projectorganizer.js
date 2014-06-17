QUnit.test( "hello test", function( assert ) {
  assert.ok( 1 == "1", "Passed!" );
});

QUnit.asyncTest("Creates hgrid", function (assert) {
        var runAlready = false;
    var $fixture = $('#qunit-fixutre');
    $fixture.append('<div id="project-grid" class="hgrid" ></div>');
        var projectbrowser = new ProjectOrganizer('#project-grid',
            {
                success: function() {

                    if(!runAlready) {
                        runAlready = true;
                        QUnit.start();
                        assert.ok(true, "Success callback called");
                        assert.notEqual($('#project-grid'), "");
                    }
                }
            });
});