  <!-- New Component Modal -->
  <div class="modal fade" id="newWiki">
    <div class="modal-dialog">
        <div class="modal-content">
        <form class="form" role="form" action="${node['url']}newnode/" method="post">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
              <h3 class="modal-title">Add New Wiki Page</h3>
            </div><!-- end modal-header -->
            <div class="modal-body">
                    <div class='form-group'>
                        <input placeholder="Component Title" name="title" type="text" class='form-control'>
                    </div>
            </div><!-- end modal-body -->
            <div class="modal-footer">
               <a href="#" class="btn btn-default" data-dismiss="modal">Close</a>
              <button id="add-component-submit" type="submit" class="btn btn-primary">OK</button>
            </div><!-- end modal-footer -->
        </form>
        </div><!-- end modal- content -->
      </div><!-- end modal-dialog -->
    </div><!-- end modal -->