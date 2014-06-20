<!-- New Component Modal -->
<div class="modal fade" id="newObAddFile">
  <div class="modal-dialog">
      <div class="modal-content">
      <form class="form" role="form" action="this" method="post">
          <div class="modal-header">
              <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
            <h3 class="modal-title">Which project do you want to add the file to?</h3>
          </div><!-- end modal-header -->

          <!-- <div class="modal-body" id="registerableProjects"> -->
          <div>

           <!--  <div id="project-search_add_file" style="">
                <div id="obDropzone" style="height: 200px; width: 200px; text-align:center; display: table-cell; vertical-align: middle; border-style: dashed; float:left; margin: 25px;">
                Drop File (or click) 
                
                </div>
                
                <img src="/static/img/triangle_right.png" style='width:50px; height:50px; margin: 100px 0px 100px 0px;display:inline;' >
                <div style="margin-top:25px; margin-right:25px; float:right;">
                <input class="typeahead" type="text" placeholder="Search projects" id = 'input_project_add_file'>
                </div>
            </div> -->

          </div>
              
      <!-- </div>end modal-body -->
          <div class="modal-footer" style="margin-top:0px;">
          <span class = "findBtn btn btn-default" id="upload_file_btn" disabled="disabled">Upload File</span>
          <span class = "findBtn btn btn-default" id="add_link_add_file" disabled="disabled" style="display: none">Upload File</span>
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
