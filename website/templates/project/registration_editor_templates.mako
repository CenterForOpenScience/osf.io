<!-- String Types -->
<script type="text/html" id="string">
  <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="text">
  <input data-bind="valueUpdate: 'keyup', event: {'keyup': $root.save}, value: value" type="text" class="form-control" />
</script>
<script type="text/html" id="match">
  <input data-bind="valueUpdate: 'keyup', event: {'keyup': $root.save}, value: value, attr.placeholder: match" type="text" class="form-control" />
</script>
<script type="text/html" id="textarea">
  <textarea data-bind="textInput: value" class="form-control"> </textarea>
</script>
<!-- Number Types -->
<script type="text/html" id="number">
  <input data-bind="valueUpdate: 'keyup', event: {'keyup': $root.save}, value: value" type="text" class="form-control">
</script>
<!-- Enum Types -->
<script type="text/html" id="choose">
  <span data-bind="template: {data: $data, name: format}"></span>
</script>

<script type="text/html" id="singleselect">
  <div data-bind="foreach: {data: options, as: 'option'}">
    <div class="radio">
      <label>
        <div class="row">
          <div class="col-md-1">
            <input type="radio" data-bind="attr.name: $parent.id, value: option" />
          </div>
          <div class="col-md-11">
            <span data-bind="text: option"></span>
          </div>
        </div>
      </label>
    </div>
  </div>
</script>

<script type="text/html" id="object">
  <span data-bind="foreach: {data: $root.iterObject($data.properties)}">
      <div data-bind="template: {data: value, name: value.type}"></div>
      <hr />
    </span>
  </span>
</script>

<!-- Base Template -->
<script type="text/html" id="editorBase">
  <div class="well" style="padding-bottom: 0px;">
    <div class="row">
      <div class="col-md-12">
        <div class="form-group">
          <label class="control-label" data-bind="text: title"></label>
          <p class="help-block" data-bind="text: description"></p>
          <span class="example-block">
            <a data-bind="click: toggleExample">Show Example</a>
            <p data-bind="visible: showExample, text: help"></p>
          </span>
          <br />
          <br />
          <div class="row">
            <div class="col-md-12">
              <div class="form-group" data-bind="css: {has-success: $data.isComplete}">
                <span data-bind="with: $root.context($data)">
                  <div data-bind="disable: $root.readonly, template: {data: $data, name: type}"></div>
                </span>
              </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</script>
<script type="text/html" id="editor">
  <span data-bind="template: {data: $data, name: 'editorBase'}"></span>
  <div class="row">
    <div class="col-md-12">
      <div class="well" data-bind="template: {data: $data, name: 'commentable'}"></div>
    </div>
  </div>
</script>

<!-- Commnetable -->
<script type="text/html" id="commentable">
    <h4> Comments </h4>
    <ul class="list-group" data-bind="foreach: {data: comments, as: 'comment'}">
        <li class="list-group-item">
            <div class="row">
                <div class="col-md-12">
                    <div class="row">
                        <div class="col-sm-9">
                            <span data-bind="text: comment.author"></span> said ...
                        </div>
                        <div class="col-sm-3">
                            <div style="text-align: right;" class="btn-group">
                                <button data-bind="disable: comment.saved,
                                   click: comment.saved.bind(null, true)" class="btn btn-success fa fa-save registration-editor-comment-save"></button>
                                <button data-bind="enable: comment.canEdit,
                                   click: comment.saved.bind(null, false)" class="btn btn-info fa fa-pencil"></button>
                                <button data-bind="enable: comment.canDelete,
                                                   click: $parent.comments.remove"
                                        class="btn btn-danger fa fa-times"></button>
                            </div>
                        </div>
                    </div>
                    <br />
                    <div class="row">
                        <div class="col-md-12 form-group">
                            <textarea class="form-control" data-bind="disable: comment.saved,
                                                        value: comment.value" type="text" placeholder="The author removed this comment"></textarea>
                        </div>
                    </div>
                </div>
        </li>
    </ul>
    <div class="input-group">
      <input class="form-control registration-editor-comment" type="text" data-bind="value: nextComment, valueUpdate: 'keyup', event: {'keyup': $root.save}" />
      <span class="input-group-btn">
        <button class="btn btn primary" data-bind="click: $data.addComment,
                                                   enable: $data.allowAddNext">Add</button>
      </span>
    </div>
</script>

<%include file="registration_editor_extensions.mako" />
