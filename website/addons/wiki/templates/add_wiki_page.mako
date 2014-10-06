  <!-- New Component Modal -->
  <div class="modal fade" id="newWiki">
    <div class="modal-dialog">
        <div class="modal-content">
        <form class="form" id="newWikiForm">
            <div class="modal-header">
                <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
              <h3 class="modal-title">Add New Wiki Page</h3>
            </div><!-- end modal-header -->
            <div class="modal-body">
                     <div id="alert" style="padding-bottom:10px;color:blue;" ></div>
                    <div class='form-group'>
                        <input id="data" placeholder="New Wiki Name" type="text" class='form-control'>
                    </div>

            </div><!-- end modal-body -->
            <div class="modal-footer">
               <a id="close" href="#" class="btn btn-default" data-dismiss="modal">Close</a>
              <button id="add-wiki-submit" type="submit" class="btn btn-primary">OK</button>
            </div><!-- end modal-footer -->
        </form>
        </div><!-- end modal- content -->
      </div><!-- end modal-dialog -->
    </div><!-- end modal -->


<script>
$(document).ready(function() {
    $('#newWiki form').submit(function(e) {
        e.preventDefault();
        $.ajax({
            type: 'POST',
            data: JSON.stringify(data.value),
            contentType: 'application/json',
            dataType: 'json',
            url: '${ api_url_for('project_wiki_edit_post', pid=node['id'], wid=pageName) }',
            success: function(data) {
                window.location.href = data.location;
            },
            error: function(response) {
                if(response.status === 409) {
                    alert('A wiki page with this name already exists.');
                }
                if(response.status === 422) {
                    alert('This is an invalid wiki page name.')
                }
            }
        });
    });
});

</script>
