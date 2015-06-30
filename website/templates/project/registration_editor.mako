<div id="registrationEditorScope">
   <div class="container">
        <div class="row">
          <div class="span8 col-md-2 columns eight large-8" data-bind="with: currentSchema">
            <ul class="nav nav-stacked list-group" data-bind="foreach: {data: pages, as: 'page'}">
              <li class="re-navbar">
                <a class="registration-editor-page" style="text-align: left; font-weight:bold;" data-bind="text: title, click: $root.selectPage">
                  <i class="fa fa-caret-right"></i>
                </a>
                <span class="btn-group-vertical" role="group">
                  <ul class="list-group" data-bind="foreach: questions">
                    <li data-bind="css: {
                                     list-group-item-success: $root.isComplete($data), 
                                     list-group-item-warning: !$root.isComplete($data)
                                   },
                                   click: $root.selectQuestion.bind($root, page),
                                   text: nav"
                        class="registration-editor-question list-group-item">
                    </li>
                  </ul>
                </span>
              </li>
            </ul>
          </div>
          <div class="span8 col-md-9 columns eight large-8">
                <a data-bind="click: previousPage" style="padding-left: 5px;">
                    <i style="display:inline-block; padding-left: 5px; padding-right: 5px;" class="fa fa-arrow-left"></i>Previous
                </a>
                <a data-bind="click: nextPage" style="float:right; padding-right:5px;">Next
                    <i style="display:inline-block; padding-right: 5px; padding-left: 5px;" class="fa fa-arrow-right"></i>
                </a>
                <!-- EDITOR -->
                <div id="registrationEditor"></div>
                <p>Last saved: <span data-bind="text: $root.lastSaved()"></span></p>
                <button data-bind="css: {disabled: disableSave},                                 
                                   click: save" type="button" class="btn btn-success">Save</button>
            </div>
        </div>
    </div>
</div>
