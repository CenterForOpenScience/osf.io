
    var data = [
        {'uid': 0, 'type': 'folder', 'name': 'skaters', 'parent_uid': 'null'},
        {'uid': 3, 'type': 'folder', 'name': 'soccer_players', 'parent_uid': 'null'},
        {'uid': 4, 'type': 'folder', 'name': 'pro', 'parent_uid': 3},
        {'uid': 7, 'type': 'folder', 'name': 'regular', 'parent_uid': 3},
        {'uid': 10, 'type': 'folder', 'name': 'bad', 'parent_uid': 7},
        {'uid': 1, 'type': 'file', 'name': 'tony', 'parent_uid': 0},
        {'uid': 2, 'type': 'file', 'name': 'bucky', 'parent_uid': 0},
        {'uid': 5, 'type': 'file', 'name': 'ronaldo', 'parent_uid': 4},
        {'uid': 6, 'type': 'file', 'name': 'messi', 'parent_uid': 4},
        {'uid': 8, 'type': 'file', 'name': 'jake', 'parent_uid': 7},
        {'uid': 9, 'type': 'file', 'name': 'robert', 'parent_uid': 7},
        {'uid': 11, 'type': 'file', 'name': 'joe', 'parent_uid': 10}
    ];

var grid = HGrid.create({
        container: "#s3Grid",
        info: gridData,
        breadcrumbBox: "#s3Crumbs",
        dropZone: true,
        url: '/',
});
  grid.addColumn({id:'id', name:'id', field:'id', sortable: true})
  grid.addColumn({id:'parent_uid', name:'Parent uid', field:'parent_uid', sortable: true})