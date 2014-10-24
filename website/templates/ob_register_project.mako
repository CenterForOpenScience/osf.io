
<!-- start #obRegisterProject -->
<li id="obRegisterProject" class="ob-list list-group-item">
    <div id="obRegisterProjectBtn" class="ob-unselectable">
        <h3 class="ob-heading" >Register a project or component</h3>
        <img class="ob-expand-icon pull-right" id="obIconRegisterProject" src="/static/img/plus.png">
    </div><!-- end #obInputProject-btn -->

    <div class="ob-reveal" id="obRevealRegisterProject">
        <div class="row">
            <div class="col-md-12" >
                <h4>1. Select Project</h4>
                <div class="ob-search" class="projectSearchRegisterProject">
                    <img class="ob-clear-button ob-reveal" id="clearInputProjectRegisterProject" src="/static/img/close2.png">
                    <input class="typeahead" type="text" placeholder="Type to search" id = 'inputProjectRegisterProject'>
                </div> <!-- end #projectSearchRegisterProject -->
            </div>
        </div><!-- end row -->

        <div class="row">
            <div class="col-md-12">
                <h4>2. Select a component (optional)</h4>
                <div class="ob-search" id="projectSearchRegisterProject">
                    <img class="ob-clear-button ob-reveal" id="clearInputComponentRegisterProject" src="/static/img/close2.png">
                    <input class="typeahead" type="text" placeholder="First select a project" disabled="disabled" id = 'inputComponentRegisterProject'>
                </div> <!-- end #projectSearchRegisterProject -->

                <span class="findBtn btn btn-primary pull-right" id="addLinkRegisterProject" disabled="disabled">Go to registration page</span>
            </div>
        </div>
    </div>
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
