   //////////////////////////////////
  // Custom asserts and utilities //
 //////////////////////////////////
  function isTrue(expr, msg) {
    return strictEqual(expr, true, msg || 'is true');
  }

  function isFalse(expr, msg) {
    return strictEqual(expr, false, msg || 'is false');
  }

  /** Trigger a Slick.Event **/
  function triggerSlick(evt, args, e) {
    e = e || new Slick.EventData();
    args = args || {};
    args.grid = self;
    return evt.notify(args, e, self);
  }

   /**
   * Checks if the selected element contains given text
   */
  function containsText(selector, text, msg) {
    var fullSelector = selector + ':contains(' + text + ')';
    return isTrue($(fullSelector).length > 0, msg || '"' + text + '" found in element(s)');
  }

  /**
   * Checks if the selected element does not contain given text
   */
  function notContainsText(selector, text, msg) {
    var fullSelector = selector + ':contains(' + text + ')';
    return equal($(fullSelector).length, 0, msg || '"' + text + '" found in element(s)');
  }

    //////////////////////////////////
   //            Tests             //
  //////////////////////////////////


QUnit.module("Verifying QUnit works at all", {});
QUnit.test('1 equals "1"', function (assert) {
    assert.ok(1 == "1", "Passed!");
});


QUnit.module("AJAX Tests", {
    setup: function (assert) {
        $.mockjaxClear();

        $.mockjax({
            url: '/api/v1/dashboard/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": true, "modifiedDelta": -5575.910912, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T16:06:19.301000", "description": null, "isProject": true, "node_id": "5wha8", "expand": true, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": false, "acceptsComponents": true, "view": true}, type: "folder", "kind": "folder", "name": "Dashboard", "isComponent": false, "parentIsFolder": false, "isRegistration": false, "apiURL": "/api/v1/project/5wha8/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": false, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/5wha8',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -25.646482, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T18:52:16.203000", "description": null, "isProject": true, "node_id": "9gm2w", "expand": false, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true},  type: "folder", "kind": "folder", "name": "2", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/9gm2w/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}, {"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -5300.049998, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T17:24:21.804000", "description": null, "isProject": true, "node_id": "zp6ji", "expand": true, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true}, type: "folder", "kind": "folder", "name": "1", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/zp6ji/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}, { type: "smart-folder", "kind": "folder", "name": "All my projects", "contributors": [], "parentIsFolder": true, "isPointer": false, "isFolder": true, "dateModified": null, "modifiedDelta": 0, "node_id": "-amp", "modifiedBy": null, "isSmartFolder": true, "urls": {"upload": null, "fetch": null}, "isDashboard": false, "children": [], "expand": false, "permissions": {"edit": false, "acceptsDrops": false, "copyable": false, "movable": false, "view": true}}, { type: "smart-folder", "kind": "folder", "name": "All my registrations", "contributors": [], "parentIsFolder": true, "isPointer": false, "isFolder": true, "dateModified": null, "modifiedDelta": 0, "node_id": "-amr", "modifiedBy": null, "isSmartFolder": true, "urls": {"upload": null, "fetch": null}, "isDashboard": false, "children": [], "expand": false, "permissions": {"edit": false, "acceptsDrops": false, "copyable": false, "movable": false, "view": true}}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/-amp',
            responseTime: 0,
            contentType: 'text/json',
            responseText: [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}, {"url": "/nqt8y/", "name": "Barrows"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -5425.354011, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T16:14:01.947000", "description": "optimize user-centric e-services", "isProject": true, "node_id": "i5yj3", "expand": true, "permissions": {"copyable": true, "edit": true, "acceptsCopies": true, "acceptsMoves": false, "acceptsFolders": false, "movable": false, "acceptsComponents": false, "view": true},  type: "project", "kind": "folder", "name": "Right-sized demand-driven budgetarymanagement", "isComponent": false, "parentIsFolder": false, "isRegistration": false, "apiURL": "/api/v1/project/i5yj3/", "urls": {"upload": null, "fetch": "/i5yj3/"}, "isFile": false, "isPointer": false, "isSmartFolder": false}]
        });
        $.mockjax({
            url: '/api/v1/dashboard/-amr',
            responseTime: 0,
            contentType: 'text/json',
            responseText: [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}, {"url": "/nqt8y/", "name": "Barrows"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -5501.727837, "modifiedBy": "McTestperson", "registeredMeta": {"Open-Ended_Registration": "{\"summary\": \"Testing\"}"}, "dateModified": "2014-07-08T16:14:01.947000", "description": "optimize user-centric e-services", "isProject": true, "node_id": "f9nhw", "expand": true, "permissions": {"copyable": true, "edit": false, "acceptsCopies": true, "acceptsMoves": false, "acceptsFolders": false, "movable": false, "acceptsComponents": false, "view": true},  type: "project", "kind": "folder", "name": "Right-sized demand-driven budgetarymanagement", "isComponent": false, "parentIsFolder": false, "isRegistration": true, "apiURL": "/api/v1/project/f9nhw/", "urls": {"upload": null, "fetch": "/f9nhw/"}, "isFile": false, "isPointer": false, "isSmartFolder": false}]
        });
        $.mockjax({
            url: '/api/v1/dashboard/9gm2w',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -6843.890789, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T18:52:16.186000", "description": null, "isProject": true, "node_id": "39hen", "expand": false, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true},  type: "folder", "kind": "folder", "name": "2-1", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/39hen/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/zp6ji',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}, {"url": "/nqt8y/", "name": "Barrows"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -4213.664841, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T17:45:27.995000", "description": "optimize user-centric e-services", "isProject": true, "node_id": "i5yj3", "expand": true, "permissions": {"copyable": true, "edit": true, "acceptsCopies": true, "acceptsMoves": false, "acceptsFolders": false, "movable": true, "acceptsComponents": false, "view": true},  type: "project", "kind": "folder", "name": "Right-sized demand-driven budgetarymanagement", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/i5yj3/", "urls": {"upload": null, "fetch": "/i5yj3/"}, "isFile": false, "isPointer": true, "isSmartFolder": false}, {"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -10167.873596, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T16:06:13.791000", "description": null, "isProject": true, "node_id": "4eyxz", "expand": true, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true}, type: "folder", "kind": "folder", "name": "1-1", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/4eyxz/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/i5yj3',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -4267.079385, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T17:45:28.024000", "description": "visualize compelling solutions", "isProject": false, "node_id": "bzny3", "expand": false, "permissions": {"copyable": true, "edit": true, "acceptsCopies": false, "acceptsMoves": false, "acceptsFolders": false, "movable": false, "acceptsComponents": false, "view": true},  type: "component", "kind": "folder", "name": "Devolved heuristic array", "isComponent": true, "parentIsFolder": false, "isRegistration": false, "apiURL": "/api/v1/project/i5yj3/node/bzny3/", "urls": {"upload": null, "fetch": "/bzny3/"}, "isFile": false, "isPointer": false, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/f9nhw',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": false, "children": [], "isDashboard": false, "modifiedDelta": -5875.182537, "modifiedBy": "McTestperson", "registeredMeta": {"Open-Ended_Registration": "{\"summary\": \"Testing\"}"}, "dateModified": "2014-07-08T16:14:01.947000", "description": "visualize compelling solutions", "isProject": false, "node_id": "5xnai", "expand": false, "permissions": {"copyable": true, "edit": false, "acceptsCopies": false, "acceptsMoves": false, "acceptsFolders": false, "movable": false, "acceptsComponents": false, "view": true},  type: "component", "kind": "folder", "name": "Devolved heuristic array", "isComponent": true, "parentIsFolder": false, "isRegistration": true, "apiURL": "/api/v1/project/f9nhw/node/5xnai/", "urls": {"upload": null, "fetch": "/5xnai/"}, "isFile": false, "isPointer": false, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/4eyxz',
            responseTime: 0,
            contentType: 'text/json',
            responseText: {"data": [{"contributors": [{"url": "/k62ps/", "name": "McTestperson"}], "isFolder": true, "children": [], "isDashboard": false, "modifiedDelta": -6423.257029, "modifiedBy": "McTestperson", "registeredMeta": {}, "dateModified": "2014-07-08T16:06:13.772000", "description": null, "isProject": true, "node_id": "ti847", "expand": true, "permissions": {"copyable": false, "edit": true, "acceptsCopies": true, "acceptsMoves": true, "acceptsFolders": true, "movable": true, "acceptsComponents": true, "view": true}, type: "folder", "kind": "folder", "name": "1-1-1", "isComponent": false, "parentIsFolder": true, "isRegistration": false, "apiURL": "/api/v1/project/ti847/", "urls": {"upload": null, "fetch": null}, "isFile": false, "isPointer": true, "isSmartFolder": false}]}
        });
        $.mockjax({
            url: '/api/v1/dashboard/bzny3',
            responseTime: 0,
            contentType: 'text/json',
            responseText: { "data": [] }
        });
        $.mockjax({
            url: '/api/v1/dashboard/39hen',
            responseTime: 0,
            contentType: 'text/json',
            responseText: { "data": [] }
        });
        $.mockjax({
            url: '/api/v1/dashboard/ti847',
            responseTime: 0,
            contentType: 'text/json',
            responseText: { "data": [] }
        });
        $.mockjax({
            url: '/api/v1/project/9gm2w/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: ["39hen"]
        });
        $.mockjax({
            url: '/api/v1/project/ti847/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: []
        });
        $.mockjax({
            url: '/api/v1/project/4eyxz/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: ["ti847"]
        });
        $.mockjax({
            url: '/api/v1/project/zp6ji/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: ["4eyxz", "i5yj3"]
        });
        $.mockjax({
            url: '/api/v1/project/5wha8/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: ["zp6ji", "9gm2w"]
        });
        $.mockjax({
            url: '/api/v1/project/39hen/get_folder_pointers/',
            responseTime: 0,
            contentType: 'text/json',
            responseText: []
        });
        $.mockjax({
            url: '/api/v1/project/*/collapse/',
            responseTime: 0,
            type: 'POST'
        });
        $.mockjax({
            url: '/api/v1/project/*/expand/',
            responseTime: 0,
            type: 'POST'
        });

        var $fixture = $('#qunit-fixutre');
        $fixture.append('<div id="project-grid" class="hgrid" ></div>');

    }
});

QUnit.asyncTest("Creates hgrid", function (assert) {
    expect(2);
    var runCount = 0;
    var projectbrowser = new ProjectOrganizer('#project-grid',
        {
            success: function () {
                var totalCallbacks = 4;
                if (runCount == totalCallbacks) {
                    QUnit.start();
                    assert.ok(true, 'Success callback called ' + totalCallbacks + ' times.');
                    assert.notEqual($('#project-grid'), "");
                } else {
                    runCount++;
                }
            }
        });
});

QUnit.asyncTest("Hgrid contents correct", function (assert) {
    expect(1);
    var runCount = 0;
    var projectbrowser = new ProjectOrganizer('#project-grid',
        {
            success: function () {
                var initialCallbacks = 4;
                if (runCount == initialCallbacks) {
                    QUnit.start();
                    var data = projectbrowser.grid.grid.getData();
                    assert.equal(data.getLength(), 9, 'Data is proper length');
                } else {
                    runCount++;
                }
            }
        });
});

QUnit.asyncTest("Hgrid expands and collapses", function (assert) {
    expect(2);
    var runCount = 0;
    var initialCallbacks = 4;
    var expandCallbacks = 6;
    var collapseCallbacks = 7;
    var projectbrowser = new ProjectOrganizer('#project-grid',
        {
            success: function () {
                if (runCount == initialCallbacks) {
                    runCount++;
                    var folder = projectbrowser.grid.getData()[8];
                    projectbrowser.grid.expandItem(folder);
                } if (runCount == expandCallbacks){
                    QUnit.start();
                    runCount++;
                    var data = projectbrowser.grid.grid.getData();
                    assert.equal(data.getLength(), 11, 'Data is proper length after expand');
                    folder = projectbrowser.grid.getData()[8];
                    projectbrowser.grid.collapseItem(folder);
                } if (runCount == collapseCallbacks) {
                    var data = projectbrowser.grid.grid.getData();
                    assert.equal(data.getLength(), 9, 'Data is proper length after collapse');
                } else {
                    runCount++;
                }
            }
        });
});

/*   QUnit.module("Helper function tests",{});

       test('whichIsContainer', function() {
        var dat = {
          data: [{
            kind: HGrid.FOLDER,
            name: '1',
            children: [{
              kind: HGrid.FOLDER,
              name: '1-1',
              children: [{
                  kind: HGrid.FOLDER,
                  name: '1-1-1',
                  children: [{
                      kind: HGrid.ITEM,
                      name: 'item'
                    }]
                }]
            },{
              kind: HGrid.FOLDER,
              name: '1-2'
            }]
          }]
        };
        var grid = new HGrid('#myGrid', {
          data: dat
        });
        var data = grid.getData();
        equal(data[0].name, '1');
        equal(data[1].name, '1-1');
        equal(data[2].name, '1-1-1');
        equal(data[3].name, 'item');
        equal(data[4].name, '1-2');
        equal(grid.whichIsContainer(0,1), 0, 'parent is container');
        equal(grid.whichIsContainer(1,0), 0, 'parent is container, reverse order of parameters');
        equal(grid.whichIsContainer(1,1), 1, 'item contains itself');
        equal(grid.whichIsContainer(0,2), 0, 'grandparent is container');
        equal(grid.whichIsContainer(2,3), 2, 'folder contains leaf');
        equal(grid.whichIsContainer(1,3), 1, 'grandparent contains leaf');
        equal(grid.whichIsContainer(2,4), null, 'nobody contains cousins');
        equal(grid.whichIsContainer(1,4), null, 'nobody contains siblings');
    });*/
