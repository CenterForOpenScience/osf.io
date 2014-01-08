


var grid = HGrid.create({
        container: "#s3Grid",
        info: gridData,
        breadcrumbBox: "#s3Crumbs",
        topCrumb: false,
        dragToRoot: false,
        dragDrop: false,
        forceFitColumns: true,
});
  grid.addColumn({id:'id', name:'id', field:'id', sortable: true})