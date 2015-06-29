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
                    <ul class="nav nav-pills nav-stacked" data-bind="foreach: {data: draft().schema.pages, as: 'page'}">
                      <li class="re-navbar">
                        <a style="text-align: left; font-weight:bold;" data-bind="text: title, click: $root.selectPage">
                            <i class="fa fa-caret-right"></i>
                        </a>
                        <span class="btn-group-vertical" role="group" data-bind="foreach: {data: page.questions, as: 'question'}">
                          <button class="btn btn-sm btn-primary" style="width: 130px"
                                  data-bind="text: question.nav, click: $root.selectQuestion.bind($root, page, question)">
                          </button>
                          <span style-"float:right;" data-bind="attr: { id: question.nav }"></span>
                        </span>
                      </li>
                    </ul>
                
                </p>
            </div>
            <div class='span8 col-md-9 columns eight large-8'>
                <a data-bind="click: previous" style="padding-left: 5px;">
                    <i style="display:inline-block; padding-left: 5px; padding-right: 5px;" class="fa fa-arrow-left"></i>Previous
                </a>
                <a data-bind="click: next" style="float:right; padding-right:5px;">Next
                    <i style="display:inline-block; padding-right: 5px; padding-left: 5px;" class="fa fa-arrow-right"></i>
                </a>
                <div id="registrationEditor"></div>
                <button data-bind="css: {disabled: disableSave},                                 
                                   click: check" type="button" class="btn btn-success">Save</button>
                <button data-bind="css: {disabled: disableSave},                                 
                                   click: uncheck" type="button" class="btn btn-warning">Mark Incomplete</button>
          </div>
    </div>
</div>
</div>

