##<%inherit file="project/addon/widget.mako"/>
<div id="evernoteWidget">
  <div>Hello ${full_name}!  folder_id: ${folder_id}</div>
  <div>hello var: <div data-bind="text: hello_var"></div></div>
  <div class="col-md-12">
    <div class="row">
      <button class="btn btn-success" data-bind="click: openAddDialog"></button>
    </div>
    <div class="row">
      <div data-bind="foreach: notes">
        <p>
          <button class="btn btn-default" data-bind="click: openEditDialog"></button>
          <button class="btn btn-danger" data-bind="click: openDeleteNoteDialog"></button>
        </p>
        <p>
          <span data-bind="text: note.title"></span>
          <p data-bind="text: note.body"></p>
        </p>
      </div>
    </div>
  </div>
</div>
