<%inherit file="project/addon/widget.mako"/>
<div id="evernoteWidget">
  <div class="evernote-test">Notebook: ${folder_name}</div>
  <div class="col-md-12">
    <table id="evernote-notes-list" class="display" cellspacing="0" width="100%">
      <tr><td>Loading notes....</td></tr>
    </table>
    <hr />
    <div id="evernote-note-title"></div>
    <div id="evernote-notedisplay"></div>
  </div>
</div>
