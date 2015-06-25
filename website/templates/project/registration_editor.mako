<div id="registrationEditorScope">
    <select class="form-control" id="registrationSchemaSelect" data-bind="options: schemas,
                           optionsText: 'title',
                           optionsValue: 'id',
                           value: selectedSchemaId">
    </select>
    <div class='container'>
        <div class='row'>
            <div class='span8 col-md-12 columns eight large-8'>
                <h2 id="schemaTitle">Select an option above</h2>
                <p>
                    <ul class="nav navbar-nav" data-bind="foreach: schema().pages">
                        <li>
                            <a style="padding-bottom:0px;" data-bind="text: title,
                                click: $root.selectPage"></a>

                            <ul class="nav navbar-nav" data-bind="foreach: schema().pages.keys">
                                <li><a style="padding-top:0px;padding-right:5px;" data-bind="text: title,
                                click: $root.selectPage"></a></li>
                            </ul>
                        </li>                
                    </ul>
                </p>
                <br />
                <br />
                <div id="registrationEditor"></div>
                <button data-bind="css: {disabled: disableSave},                                 
                                 click: save" type="button" class="btn btn-success">Save</button>
            </div>
        </div>
    </div>
</div>
