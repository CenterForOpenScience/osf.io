<!-- String Types -->
<script type="text/html" id="string">
  <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="text">
  <input data-bind="valueUpdate: 'keyup',
                    value: value"
         type="text" class="form-control" />
</script>
<script type="text/html" id="match">
  <input data-bind="valueUpdate: 'keyup',
                    value: value,
                    attr: {placeholder: match}" type="text" class="form-control" />
</script>
<script type="text/html" id="textarea">
  <textarea data-bind="valueUpdate: 'keyup',
                       textInput: value"
            class="form-control"> </textarea>
</script>
<!-- Number Types -->
<script type="text/html" id="number">
  <input data-bind="valueUpdate: 'keyup',
                    value: value" type="text" class="form-control">
</script>
<!-- Enum Types -->
<script type="text/html" id="choose">
  <span data-bind="template: {data: $data, name: format}"></span>
</script>
<script type="text/html" id="singleselect">
  <div class="col-md-12" data-bind="foreach: {data: options, as: 'option'}">
    <p data-bind="if: !Boolean(option.tooltip)">
      <input type="radio" data-bind="checked: $parent.value,
                                     value: option"/>
      <span data-bind="text: option"></span>
    </p>
    <p data-bind="if: Boolean(option.tooltip)">
      <input type="radio" data-bind="checked: $parent.value,
                                     value: option.text"/>
        <label data-bind="text: option.text"></label>
      <span data-bind="tooltip: {title: option.tooltip}" class="fa fa-info-circle"></span>
    </p>
  </div>
</script>
<script type="text/html" id="multiselect">
  <div class="col-md-12" data-bind="foreach: {data: options, as: 'option'}">
    <p data-bind="if: !Boolean(option.tooltip)">
      <input type="checkbox" data-bind="attr: {value: option},
                                        checked: $parent.value,
                                        checkedValue: option" />
      <span data-bind="text: option"></span>
    </p>
    <p data-bind="if: Boolean(option.tooltip)"> <!-- TODO: Verify checkboxes -->
      <input type="checkbox" data-bind="attr: {value: option.text},
                                        checked: $parent.value,
                                        checkedValue: option">
      <span data-bind="text: option.text, tooltip: {title: option.tooltip}"></span>
    </p>
  </div>
</script>

<script type="text/html" id="object">
  <span data-bind="foreach: $data.properties">
    <div data-bind="template: {data: $root.context($data, $root), name: $data.type}"></div>
    <hr />
  </span>
</script>

<!-- Base Template -->
<script type="text/html" id="editorBase">
  <div class="well" style="padding-bottom: 0px;">
    <div class="row">
      <div class="col-md-12">
        <div class="form-group">
          <label class="control-label" data-bind="text: title"></label>
          <span class="text-muted" data-bind="if: required, tooltip: {title: 'This field is required for submission. If this field is not applicable to your study, you may state so.'}">
            (required)
          </span>
          <span class="text-muted" data-bind="ifnot: required">
            (optional)
          </span>
          <p class="help-block" data-bind="text: description"></p>
          <span data-bind="if: help" class="example-block">
            <a data-bind="click: toggleExample">Show Example</a>
            <p data-bind="visible: showExample, html: help"></p>
          </span>
          <br />
          <div class="row">
            <div class="col-md-12">
              <div class="form-group">
                <span data-bind="with: $root.context($data, $root)">
                  <span data-bind="if: $root.showValidation">
                    <ul class="list-group" data-bind="foreach: $data.validationInfo()">
                      <li class="list-group-item">
                        <span class="text-danger"
                              data-bind="text: $data">
                        </span>
                      </li>
                    </ul>
                  </span>
                  <div data-bind="template: {data: $data, name: type}"></div>
                  <br />
                </span>
              </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  </div>
</script>

<script type="text/html" id="editor">
  <span data-bind="if: $data.description">
    <div class="well">
      <blockquote>
        <p data-bind="html: description"></p>
      </blockquote>
    </div>
  </span>
  <div data-bind="foreach: {data: $data.questions, as: 'question'}">
    <span data-bind="template: {data: $data, name: 'editorBase'}"></span>
  </div>
  <div class="row" data-bind="if: $root.draft().requiresApproval">
    <div class="col-md-12" data-bind="if: comments().length">
      <div class="well" data-bind="template: {data: $data, name: 'commentable'}"></div>
    </div>
  </div>
</script>

<!-- Commentable -->
<script type="text/html" id="commentable">
  <div class="registration-editor-comments">
    <h4> Comments </h4>
    <ul class="list-group" id="commentList" data-bind="foreach: {data: comments, as: 'comment'}">
        <li class="list-group-item">
          <div class="row" data-bind="visible: comment.isDeleted">
            <div class="col-md-12">
              <strong><span data-bind="text: comment.getAuthor"></span></strong> deleted this comment on <em data-bind="text: comment.lastModified"></em>
            </div>
          </div>
          <span class="row" data-bind="visible: !comment.isDeleted()">
            <div class="row">
              <div class="col-md-12">
                <div class="row">
                  <div class="col-sm-9">
                    <strong><span data-bind="text: comment.getAuthor"></span></strong> said ...
                  </div>
                  <div data-bind="if: comment.isOwner" class="col-sm-3">
                    <div style="text-align: right;" class="btn-group">
                      <button data-bind="disable: comment.saved,
                                         click: comment.toggleSaved.bind(comment, $root.save.bind($root))" class="btn btn-success fa fa-save registration-editor-comment-save"></button>
                      <button data-bind="enable: comment.canEdit,
                                         click: comment.toggleSaved.bind(comment, $root.save.bind($root))" class="btn btn-info fa fa-pencil"></button>
                      <button data-bind="enable: comment.canDelete,
                                         click: comment.delete.bind(comment, $root.save.bind($root)) "
                              class="btn btn-danger fa fa-times"></button>
                    </div>
                  </div>
                </div>
                <br />
                <div class="row" data-bind="if: comment.isOwner">
                  <div class="col-md-12 form-group">
                    <textarea class="form-control"
                              style="resize: none; overflow: scroll"
                              data-bind="disable: comment.saved,
                                         value: comment.value" type="text"></textarea>
                  </div>
                </div>
                <div class="col-md-12" data-bind="ifnot: comment.isOwner">
                  <span data-bind="text: comment.value"></span>
                </div>
              </div>
            </div>
          </span>
        </li>
    </ul>
    <div class="input-group">
      <input class="form-control registration-editor-comment" type="text"
             data-bind="value: currentQuestion.nextComment,
                        valueUpdate: 'keyup'" />
      <span class="input-group-btn">
        <button class="btn btn-primary"
                data-bind="click: currentQuestion.addComment.bind(
                             currentQuestion,
                             $root.save.bind($root)
                           ),
                           enable: currentQuestion.allowAddNext">Add</button>
      </span>
    </div>
  </div>
</script>
<%include file="registration_editor_extensions.mako" />
