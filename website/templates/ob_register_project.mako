
<!-- start #obRegisterProject -->
<li id="obRegisterProject" class="ob-list list-group-item">
    <div id="obRegisterProjectBtn" class="ob-unselectable">
        <h3 class="ob-heading" >Register a project</h3>
        <img class="ob-expand-icon pull-right" id="obIconRegisterProject" src="/static/img/plus.png">
    </div><!-- end #obInputProject-btn -->

    <div class="ob-reveal" id="obRevealRegisterProject">
        <div class="row">
            <div class="col-md-12" >
                <div class="ob-search" class="projectSearchRegisterProject">
                    <img class="ob-clear-button ob-reveal" id="clearInputProjectRegisterProject" src="/static/img/close2.png">
                    ## Add label for proper spacing
                    <label for="project"></label>
                    <input
                        data-bind="projectSearch: {url: 'api/v1/dashboard/get_nodes'}" class="typeahead form-control" name="project" type="text" placeholder="Type to search for a project or component" id = 'inputProjectRegisterProject'>
                </div> <!-- end #projectSearchRegisterProject -->
                <span class="findBtn btn btn-default pull-right" id="addLinkRegisterProject" disabled="disabled">Go to registration page</span>
            </div>
        </div><!-- end row -->
    </div><!-- end ob-reveal -->
</li> <!-- end #obInputProject" -->

<script>
// new registration js
    $('#obRegisterProjectBtn').one("click", obOpenRegisterProject);

    function obOpenRegisterProject() {
        $('#obRevealRegisterProject').show();
        $(this).one("click", obCloseRegisterProject);
        $('#obIconRegisterProject').attr('src', "/static/img/minus.png")
    }

    function obCloseRegisterProject() {
        $('#obRevealRegisterProject').hide();
        $(this).one("click", obOpenRegisterProject);
        $('#obIconRegisterProject').attr('src', "/static/img/plus.png")
    }
</script>
