<%inherit file="contentContainer.mako" />

<h2>Create New Project</h2>
<%include file="form.mako" args="
    form=form,
    name='newProject',
    actionString='/project/new', 
    formClass='form-stacked', 
    submitString='Create New Project'
"/>