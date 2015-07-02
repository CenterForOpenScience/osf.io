<div id="registrationEditorScope">
    <div class="container">
        <div class="row">
            <div class="span8 col-md-2 columns eight large-8">
                <ul class="nav nav-stacked list-group" data-bind="foreach: {data: currentPages, as: 'page'}">
                    <li class="re-navbar">
                        <a class="registration-editor-page" style="text-align: left; font-weight:bold;" data-bind="text: title, click: $root.selectPage">
                            <i class="fa fa-caret-right"></i>
                        </a>
                        <span class="btn-group-vertical" role="group">
                  <ul class="list-group" data-bind="foreach: questions">
                    <li data-bind="css: {
                                     list-group-item-success: $root.isComplete($data), 
                                     list-group-item-warning: !$root.isComplete($data),
                                     registration-editor-question-current: $root.isCurrent($parentContext.$index(), $index())
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
                <p>Last saved: <span data-bind="text: $root.lastSaved()"></span>
                </p>
                <button data-bind="disable: disableSave, 
                                   click: save" type="button" class="btn btn-success">Save
                </button>
                <hr />
                <div class="well">
                  <h4> Comments </h4>
                  <ul class="list-group" data-bind="foreach: {data: comments, as: 'comment'}">                    <li class="list-group-item">
                      <div class="row">
                        <div class="col-md-12">
                          <div class="row">
                            <div class="col-sm-9">
                            <span data-bind="text: comment.author"></span> said ...
                            </div>
                            <div class="col-sm-3">
                            <div style="text-align: right;" class="btn-group">
                              <button data-bind="disable: comment.saved,
                                            click: comment.saved.bind(null, true)" 
                                      class="btn btn-success fa fa-save registration-editor-comment-save"></button>
                              <button data-bind="enable: comment.canEdit,
                                                 click: comment.saved.bind(null, false)"
                                      class="btn btn-info fa fa-pencil"></button>
                              <button data-bind="enable: comment.canDelete,
                                                 click: $root.comments.remove"
                                      class="btn btn-danger fa fa-times"></button>
                            </div>                               
                            </div>
                          </div>
                          <br />
                          <div class="row">
                            <div class="col-md-12 form-group">
                              <textarea class="form-control"
                                        data-bind="disable: comment.saved,
                                                   value: comment.value" 
                                        type="text" placeholder="The author removed this comment"></textarea>
                            </div>
                          </div>
                        </div>
                    </li>
                  </ul>
                  <div class="input-group">                    
                    <input class="form-control registration-editor-comment" type="text" data-bind="value: $root.nextComment, valueUpdate: 'keyup'" />
                    <span class="input-group-btn" >
                      <button class="btn btn primary" data-bind="click: addComment,
                                                                 enable: $root.allowAddNext">Add</button>
                    </span>
                  </div>
                </div>                               
            </div>
        </div>
    </div>
</div>
