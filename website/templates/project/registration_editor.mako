<div id="registrationEditorScope">
  <select class="form-control" id="registrationSchemaSelect" data-bind="options: schemas,
                                                                        optionsText: 'title',
                                                                        optionsValue: 'id',
                                                                        value: selectedSchemaName">
    <option data-bind="if: draft().schemaName" value="" disabled selected>Please select a registration form to initiate registration</option>
  </select>
  <div class="container">
        <div class='row'>
            <div class="span8 col-md-12 columns eight large-8">
                <h2 id="schemaTitle">Select an option above</h2>
                <p>
                  <div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1">
                    <ul class="nav navbar-nav" data-bind="foreach: {data: draft().schema.pages, as: 'page'}">
                      <li style="padding: 2px; margin: 3px;" class="re-navbar">
                        <a style="text-align: center" data-bind="text: title, click: $root.selectPage"></a>
                        <span data-bind="foreach: {data: page.questions, as: 'question'}">
                          <buttom class="btn btn-sm btn-primary" 
                                  data-bind="text: question.id, click: $root.selectQuestion.bind($root, page, question)">
                          </button>
                        </span>
                      </li>
                    </ul>
                  </div>
                </p>
                <br />
                <br />
                <br />
                <div id="registrationEditor"></div>
                <button data-bind="css: {disabled: disableSave},                                 
                                   click: save" type="button" class="btn btn-success">Save</button>
          </div>
    </div>
</div>
</div>
