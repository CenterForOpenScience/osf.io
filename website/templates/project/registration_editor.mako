<div id="registrationEditorScope">
  <div class="container">
        <div class="row">
          <div class="span8 col-md-2 columns eight large-8" data-bind="with: currentSchema">
            <ul class="nav nav-stacked list-group" data-bind="foreach: {data: pages, as: 'page'}">
              <li class="re-navbar">
                <a style="text-align: left; font-weight:bold;" data-bind="text: title, click: $root.selectPage">
                  <i class="fa fa-caret-right"></i>
                </a>
                <span class="btn-group-vertical" role="group">
                  <ul class="list-group" data-bind="foreach: questions">
                    <li class="list-group-item">
                      <a data-bind="text: nav, click: $root.selectQuestion.bind($root, page, $data)"></a>
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
                <div id="registrationEditor"></div>
                <button data-bind="css: {disabled: disableSave},                                 
                                   click: check" type="button" class="btn btn-success">Save</button>
                <button data-bind="css: {disabled: disableSave},                                 
                                   click: uncheck" type="button" class="btn btn-warning">Mark Incomplete</button>
            </div>
        </div>
    </div>
</div>
