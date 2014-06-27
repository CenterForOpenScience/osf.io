QUnit.test("hello test", function (assert) {
    assert.ok(1 == "1", "Passed!");
});


QUnit.module("AJAX Tests", {
    setup: function () {
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/',
            contentType: 'text/json',
            responseText: {
                "data": [
                    {
                        "contributors": [{
                            "url": "/uyi58/",
                            "name": "Geiger"
                        }],
                        "isFolder": true,
                        "children": [],
                        "isDashboard": true,
                        "modifiedDelta": -539726.450663,
                        "modifiedBy": "Geiger",
                        "registeredMeta": {},
                        "dateModified": "2014-06-20T17:50:39.203000",
                        "description": null,
                        "isProject": true,
                        "node_id": "v3uqf",
                        "expand": true,
                        "permissions": {
                            "copyable": false,
                            "edit": true,
                            "acceptsCopies": true,
                            "acceptsMoves": true,
                            "acceptsFolders": true,
                            "movable": false,
                            "acceptsComponents": true,
                            "view": true
                        },
                        "kind": "folder",
                        "name": "Dashboard",
                        "isComponent": false,
                        "parentIsFolder": false,
                        "isRegistration": false,
                        "apiURL": "/api/v1/project/v3uqf/",
                        "urls": {
                            "upload": null,
                            "fetch": null
                        },
                        "isFile": false,
                        "isPointer": false,
                        "isSmartFolder": false
                    }
                ]
            }
        });
        $.mockjax({
            url: '/api/v1/dashboard/get_dashboard/v3uqf',
            contentType: 'text/json',
            responseText: {
                "data": [
                    {
                        "apiURL": "/api/v1/project/bm6zi/",
                        "children": [],
                        "contributors": [
                            {
                                "name": "Geiger",
                                "url": "/uyi58/"
                            }
                        ],
                        "dateModified": "2014-06-21T00:18:20.509000",
                        "description": null,
                        "expand": true,
                        "isComponent": false,
                        "isDashboard": false,
                        "isFile": false,
                        "isFolder": true,
                        "isPointer": true,
                        "isProject": true,
                        "isRegistration": false,
                        "isSmartFolder": false,
                        "kind": "folder",
                        "modifiedBy": "Geiger",
                        "modifiedDelta": -516836.597756,
                        "name": "Two",
                        "node_id": "bm6zi",
                        "parentIsFolder": true,
                        "permissions": {
                            "acceptsComponents": true,
                            "acceptsCopies": true,
                            "acceptsFolders": true,
                            "acceptsMoves": true,
                            "copyable": false,
                            "edit": true,
                            "movable": true,
                            "view": true
                        },
                        "registeredMeta": {},
                        "urls": {
                            "fetch": null,
                            "upload": null
                        }
                    },
                    {
                        "apiURL": "/api/v1/project/uwkme/",
                        "children": [],
                        "contributors": [
                            {
                                "name": "Geiger",
                                "url": "/uyi58/"
                            }
                        ],
                        "dateModified": "2014-06-20T18:11:27.832000",
                        "description": null,
                        "expand": true,
                        "isComponent": false,
                        "isDashboard": false,
                        "isFile": false,
                        "isFolder": true,
                        "isPointer": true,
                        "isProject": true,
                        "isRegistration": false,
                        "isSmartFolder": false,
                        "kind": "folder",
                        "modifiedBy": "Geiger",
                        "modifiedDelta": -538849.280825,
                        "name": "One",
                        "node_id": "uwkme",
                        "parentIsFolder": true,
                        "permissions": {
                            "acceptsComponents": true,
                            "acceptsCopies": true,
                            "acceptsFolders": true,
                            "acceptsMoves": true,
                            "copyable": false,
                            "edit": true,
                            "movable": true,
                            "view": true
                        },
                        "registeredMeta": {},
                        "urls": {
                            "fetch": null,
                            "upload": null
                        }
                    },
                    {
                        "children": [],
                        "contributors": [],
                        "dateModified": null,
                        "expand": false,
                        "isDashboard": false,
                        "isFolder": true,
                        "isPointer": false,
                        "isSmartFolder": true,
                        "kind": "folder",
                        "modifiedBy": null,
                        "modifiedDelta": 0,
                        "name": "All my projects",
                        "node_id": "-amp",
                        "parentIsFolder": true,
                        "permissions": {
                            "acceptsDrops": false,
                            "copyable": false,
                            "edit": false,
                            "movable": false,
                            "view": true
                        },
                        "urls": {
                            "fetch": null,
                            "upload": null
                        }
                    },
                    {
                        "children": [],
                        "contributors": [],
                        "dateModified": null,
                        "expand": false,
                        "isDashboard": false,
                        "isFolder": true,
                        "isPointer": false,
                        "isSmartFolder": true,
                        "kind": "folder",
                        "modifiedBy": null,
                        "modifiedDelta": 0,
                        "name": "All my registrations",
                        "node_id": "-amr",
                        "parentIsFolder": true,
                        "permissions": {
                            "acceptsDrops": false,
                            "copyable": false,
                            "edit": false,
                            "movable": false,
                            "view": true
                        },
                        "urls": {
                            "fetch": null,
                            "upload": null
                        }
                    }
                ]
            }
        });
        $.mockjax({
            url: 'http://localhost:5000/api/v1/dashboard/get_dashboard/-amp',
            contentType: 'text/json',
            responseText: [
            {
                "apiURL": "/api/v1/project/8jxuz/",
                "children": [],
                "contributors": [
                    {
                        "name": "Geiger",
                        "url": "/uyi58/"
                    },
                    {
                        "name": "Ryan",
                        "url": "/bc4qw/"
                    }
                ],
                "dateModified": "2014-06-17T15:42:14.287000",
                "description": "maximize e-business content",
                "expand": false,
                "isComponent": false,
                "isDashboard": false,
                "isFile": false,
                "isFolder": false,
                "isPointer": false,
                "isProject": true,
                "isRegistration": false,
                "isSmartFolder": false,
                "kind": "folder",
                "modifiedBy": "Geiger",
                "modifiedDelta": -807733.576241,
                "name": "User-friendly dynamic definition",
                "node_id": "8jxuz",
                "parentIsFolder": false,
                "permissions": {
                    "acceptsComponents": false,
                    "acceptsCopies": true,
                    "acceptsFolders": false,
                    "acceptsMoves": false,
                    "copyable": true,
                    "edit": true,
                    "movable": false,
                    "view": true
                },
                "registeredMeta": {},
                "urls": {
                    "fetch": "/8jxuz/",
                    "upload": null
                }
            }]
        });
        $.mockjax({
            url: 'http://localhost:5000/api/v1/dashboard/get_dashboard/-amr',
            contentType: 'text/json',
            responseText: [{
                "apiURL": "/api/v1/project/jn9sf/",
                "children": [],
                "contributors": [
                    {
                        "name": "Geiger",
                        "url": "/uyi58/"
                    },
                    {
                        "name": "Wuckert",
                        "url": "/psezb/"
                    }
                ],
                "dateModified": "2014-06-18T21:43:34.748000",
                "description": "redefine impactful portals",
                "expand": false,
                "isComponent": false,
                "isDashboard": false,
                "isFile": false,
                "isFolder": false,
                "isPointer": false,
                "isProject": true,
                "isRegistration": true,
                "isSmartFolder": false,
                "kind": "folder",
                "modifiedBy": "Geiger",
                "modifiedDelta": -699832.9042,
                "name": "Total 24hour opensystem",
                "node_id": "jn9sf",
                "parentIsFolder": false,
                "permissions": {
                    "acceptsComponents": false,
                    "acceptsCopies": true,
                    "acceptsFolders": false,
                    "acceptsMoves": false,
                    "copyable": true,
                    "edit": false,
                    "movable": false,
                    "view": true
                },
                "registeredMeta": {
                    "Open-Ended_Registration": "{\"summary\": \"test\"}"
                },
                "urls": {
                    "fetch": "/jn9sf/",
                    "upload": null
                }
            }]
        });
    }
});


QUnit.asyncTest("Creates hgrid", function (assert) {
    var runAlready = false;
    var $fixture = $('#qunit-fixutre');
    $fixture.append('<div id="project-grid" class="hgrid" ></div>');
    var projectbrowser = new ProjectOrganizer('#project-grid',
        {
            success: function () {

                if (!runAlready) {
                    runAlready = true;
                    QUnit.start();
                    assert.ok(true, "Success callback called");
                    assert.notEqual($('#project-grid'), "");
                }
            }
        });
});
