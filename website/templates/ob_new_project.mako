<!-- start #obNewProject -->
            <%include file="project/new_project_form.mako"/>

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
