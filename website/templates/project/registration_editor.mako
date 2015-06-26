<div id="registrationEditorScope">
    <select class="form-control" id="registrationSchemaSelect" 
            data-bind="options: schemas,
                       optionsText: 'title',
                       optionsValue: 'id',
                       value: selectedSchemaName">      
      <option data-bind="if: draft().schemaName" value="" disabled selected>Please select a registration form to initiate registration</option>
  </select>

    <div class='container'>
        <H1>Pre-reg Prize Questionnaire</H1>
        <div class='row'>
            <div class='span8 col-md-2 columns eight large-8'>
                <p>
                    <ul class="nav nav-pills nav-stacked" data-toggle="collapse" data-bind="foreach: draft().schema.pages">
                        <li>
                            <a data-bind="text: title,
                                click: $root.selectPage"></a>

                            <ul class="nav nav-pills nav-stacked" data-bind="foreach: $root.draft().schema.pages[$index()].questions">
                                <li><a data-bind="text: nav, click: $root.selectQuestion"></a></li>
                            </ul>
                        </li>                
                    </ul>
                </p>
            </div>
            <div class='span8 col-md-10 columns eight large-8'>
                <div id="registrationEditor"></div>
                <button data-bind="css: {disabled: disableSave},                                 
                                 click: save" type="button" class="btn btn-success">Save</button>
            </div>
        </div>
    </div>
</div>
