<%inherit file="project/addon/widget.mako"/>
<div id="evernoteWidget">
  <div class="evernote-test">Notebook: ${folder_name}</div>
  <div class="col-md-12">
    <%doc>
    <div class="row">
      <button class="btn btn-success" data-bind="click: openAddDialog"></button>
    </div>
    </%doc>

    <div class="row">
        <div data-bind="foreach: notes">
          <p>
            <button class="btn btn-default btn-evernote" data-bind="click: $parent.openEditDialog"
                title="Open Edit Dialog"></button>
            <button class="btn btn-danger btn-evernote" data-bind="click: $parent.openDeleteNoteDialog"
                title="Open Delete Note Dialog"></button>
            <span data-bind="text: title"></span>
          </p>
        </div>
        <div id="evernote-notedisplay"></div>
      </div>

  </div>
</div>
