<%def name="stylesheets()">
    ${parent.stylesheets()}
    <link rel="stylesheet" href="/static/css/pages/wiki-page.css">
</%def>
<!-- Sort Component Modal -->
<div class="modal fade" id="sortWiki">
    <div class="modal-dialog sort-modal-dialog">
        <div class="modal-content">
            <form class="form">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
                    <h3 draggable="true" class="modal-title">${_("Reorder Wiki Tree")}</h3>
                </div><!-- end modal-header -->
                <div class="modal-body sort-modal-body">
                    <h3 class="sort-title">${_("Wiki Tree")}</h3>
                    <div id="manageWikitree" class="scripted">
                        <ul class="sort-tree" data-bind="sortable: {template: 'wikitreeRow', data: $root.data, afterMove: $root.afterMove, beforeMove: $root.beforeMove}"></ul>
                    </div>
                </div><!-- end modal-body -->
                <div class="modal-footer sort-modal-footer">
                    <a id="close" class="btn btn-default" data-dismiss="modal">${_("Close")}</a>
                    <button id="treeSave" data-bind="click: submit" id="add-wiki-submit" type="submit" class="btn btn-success" disabled>${_("Save")}</button>
                </div><!-- end modal-footer -->
            </form>
        </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
</div><!-- end modal -->

<script id="wikitreeRow" type="text/html">
  <li data-bind="attr: {class: $parent.id}">
    <!-- ko if: $data.name -->
    <div class="sort-item" data-bind="attr: {class: 'sort-item', id: $data.id}, event: { click: $data.expandOrCollapse}">
    <div style="display: inline;"><i class="fa fa-bars sort-bars"></i></div>
    <!-- ko if: $data.children().length -->
    <div class="sort-expand-collapse-icon" style="display: inline;"><i class="fa fa-angle-down angle"></i></div>
    <!-- /ko -->
    <!-- ko ifnot: $data.children().length -->
    <div class="sort-no-icon" style="display: inline;"><i></i></div>
    <!-- /ko -->
    <div class="sort-page-name" style="display: inline;"><a data-bind="text: $data.name, click: function(){ window.open($root.url + $data.name(), '_blank');}"></a></div>
    </div>
    <!-- /ko -->
    <!-- ko if: $data.children() -->
    <ul class="sort-children" data-bind="sortable: { template: 'wikitreeRow', data: $data.children, afterMove: $root.afterMove, beforeMove: $root.beforeMove}"></ul>
    <!-- /ko -->
  </li>
</script>