<%inherit file="project/addon/widget.mako"/>
<div id="evernoteWidget">
  <div class="evernote-test">Notebook: ${folder_name}</div>
  <div class="col-md-12">
    <table id="evernote-notes-list" class="display" cellspacing="0" width="100%">
          <%doc>
          <thead>
              <tr>
                  <th>Edit</th>
                  <th>Delete</th>
                  <th>Title</th>
              </tr>
          </thead>


          <tbody data-bind="foreach: notes">
              <tr>
                <td><button class="btn btn-default btn-evernote" data-bind="click: $parent.openEditDialog"
                    title="Open Edit Dialog"></button></td>
                <td><button class="btn btn-danger btn-evernote" data-bind="click: $parent.openDeleteNoteDialog"
                    title="Open Delete Note Dialog"></button></td>
                <td><span data-bind="text: title"></span></td>
              </tr>
          </tbody>
          </%doc>

    </table>
    <div id="evernote-notedisplay"></div>
  </div>
</div>
