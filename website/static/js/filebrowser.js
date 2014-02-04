/**
 * Module to render the consolidated files view. Reads addon configurrations and
 * initializes an HGrid.
 */
this.FileBrowser = (function($, HGrid, global) {

  // Aliases
  var asItem = HGrid.Fmt.asItem;
  var withIndent = HGrid.Fmt.withIndent;
  var sanitized = HGrid.Fmt.sanitized;

  // Can't use microtemplate because microtemplate escapes html
  HGrid.Col.Name.folderView = function (item) {
    return HGrid.Html.folderIcon + item.name;
  };

  // TODO: This doesn't work yet.
  function refreshGitHubTree(grid, item, branch) {
      var parentID = item.parentID;
      var data = item.data || {};
      data.branch = branch;
      $.ajax({
        type: 'get',
        url: item.lazyLoad + 'dummy/?branch=' + branch,
        success: function(response) {
          grid.removeFolder(item);
          response.parentID = parentID;
          grid.addItem(response);
          grid.expandItem(response);
        }
      });
  }

  hgridOptions = {
    columns: [
        HGrid.Col.Name,
        HGrid.Col.ActionButtons
    ],
    fetchUrl: function(row) {
      return row.urls.fetch;
    },
    downloadUrl: function(row) {
      return row.urls.download;
    },
    deleteUrl: function(row) {
      return row.urls.delete;
    },
    deleteMethod: 'delete',
    uploads: true,
    uploadUrl: function(row) {
      return row.urls.upload;
    },
    uploadMethod: 'post',
    uploadSuccess: function(file, item, data) {
      data.parentID = item.parentID;
      this.removeItem(item.id);
      this.addItem(data);
    },
    listeners: [
      // Go to file's detail page if name is clicked
      {on: 'click', selector: '.hg-item-content',
      callback: function(evt, row, grid) {
        if (row) {
          var viewUrl = grid.getByID(row.id).urls.view;
          if (viewUrl) {
              window.location.href = viewUrl;
          }
        }
      }},
      {on: 'change', selector: '.github-branch-select',
      callback: function(evt, row, grid) {
        var $this = $(evt.target);
        var id = row.id;
        var item = grid.getByID(id);
        var branch = $this.val();
        refreshGitHubTree(grid, item, branch);
      }}
    ]
  };

  function FileBrowser(selector, options){
    this.selector = selector;
    var opts = $.extend({}, hgridOptions, options);
    this.options = opts;
    this.grid = new HGrid(selector, opts);
  }

  FileBrowser.prototype = {
      // methods
  };

  return FileBrowser;

})(jQuery, HGrid, window);



