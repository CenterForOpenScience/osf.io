

var grid = HGrid.create({
        container: "#s3Grid",
        info: gridData,
        breadcrumbBox: "#s3Crumbs",
        dropZone: true,
        url: '/',
});
  grid.addColumn({id:'id', name:'id', field:'id', sortable: true})
  grid.addColumn({id:'parent_uid', name:'Parent uid', field:'parent_uid', sortable: true})