<!-- start #obNewProject -->
    <li id="obNewProject" class="ob-list-item list-group-item">
        <div id="obNewProjectBtn" class="ob-reveal-btn ob-unselectable">
            <h3 class="ob-heading">Create a new project</h3>
            <img class="ob-expand-icon pull-right" id="obIconNewProject" src="/static/img/plus.png">
        </div><!-- end .obNewProjectBtn -->

    <div class="ob-reveal" id="obRevealNewProject">
            <br>
            <%include file="project/new_project_form.mako"/>
    </div>
    </li> <!-- end #obNewProject" -->

<script>
// new project js
$('#obNewProjectBtn').one("click", obOpenNewProject);

function obOpenNewProject() {
    $('#obRevealNewProject').show();
    $(this).one("click", obCloseNewProject);
    $('#obIconNewProject').attr('src', "/static/img/minus.png")
}

function obCloseNewProject() {
    $('#obRevealNewProject').hide();
    $(this).one("click", obOpenNewProject);
    $('#obIconNewProject').attr('src', "/static/img/plus.png")
}

// button disabler for new project form
$('#projectForm').on('submit',function(){
    $('button[type="submit"]', this)
        .attr('disabled', 'disabled')
        .text('Creating');
});
</script>
