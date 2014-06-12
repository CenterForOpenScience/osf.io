<!-- New Component Modal -->
<div class="modal fade" id="newObRegistration">
  <div class="modal-dialog">
      <div class="modal-content">
      <form class="form" role="form" action="this" method="post">
          <div class="modal-header">
              <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
            <h3 class="modal-title">Select the project you want to register</h3>
          </div><!-- end modal-header -->

          <!-- <div class="modal-body" id="registerableProjects"> -->
          <div>
            <div id="project-search_register_project">
              <input class="typeahead" type="text" placeholder="Search projects" style="margin:20px;" 
                    id = 'input_project_register_project'>
            </div>
          </div>
              
      <!-- </div>end modal-body -->
          <div class="modal-footer">
          <span class = "findBtn btn btn-default" id="add_link_register_project" disabled="disabled">Go to registration page</span>
              <a id='confirm' href="#" class="btn btn-default" data-dismiss="modal">Close</a>

          </div><!-- end modal-footer -->
      </form>
      </div><!-- end modal- content -->
    </div><!-- end modal-dialog -->
  </div><!-- end modal -->
<script type="text/javascript">
      $(document).ready(function() {
          $('#confirm').on('click',function(){
              $("#alert").text("");
              $("#title").val("");
              $("#category").val("");
          })

      });
</script>
