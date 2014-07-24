  <!-- New Component Modal -->
  <div class="modal fade" id="newWiki">
    <div class="modal-dialog">
        <div class="modal-content">
        <form class="form">
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


  <script type="text/javascript">

  $(function(){

      $('#newWiki form').on('submit', function(e) {

          e.preventDefault();
          $("#add-wiki-submit")
                  .attr("disabled", "disabled")
                  .text("Creating New Wiki page");

          if ($.trim($("#data").val())==''){

              $("#alert").text("The new wiki page name cannot be empty");

              $("#add-wiki-submit")
                      .removeAttr("disabled", "disabled")
                      .text("OK");
          }
          else if ($(e.target).find("#data").val().length>100){
              $("#alert").text("The new wiki page name cannot be more than 100 characters.");

              $("#add-wiki-submit")
                      .removeAttr("disabled", "disabled")
                      .text("OK");
          }
          else{
              var url=document.location.href;
              var url_root = url.substr(0, url.indexOf('wiki')+5);
              var wikiName = $("#data").val()
              if (wikiName.indexOf("/") != -1){
                  wikiName = wikiName.split("/").join("|");
              }
              document.location= url_root + wikiName+ '/edit/';
          }
     });

      $('#close').on('click', function(){
          $("#alert").text("");
          $('#data').val("");
      });
  });
  </script>