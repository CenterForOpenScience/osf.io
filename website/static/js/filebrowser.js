this.FileBrowser = (function($, HGrid, global) {

  // Aliases
  var asItem = HGrid.Fmt.asItem;
  var withIndent = HGrid.Fmt.withIndent;
  var sanitized = HGrid.Fmt.sanitized;

  var extensions = ['3gp', '7z', 'ace', 'ai', 'aif', 'aiff', 'amr', 'asf', 'asx', 'bat', 'bin', 'bmp', 'bup',
    'cab', 'cbr', 'cda', 'cdl', 'cdr', 'chm', 'dat', 'divx', 'dll', 'dmg', 'doc', 'docx', 'dss', 'dvf', 'dwg',
    'eml', 'eps', 'exe', 'fla', 'flv', 'gif', 'gz', 'hqx', 'htm', 'html', 'ifo', 'indd', 'iso', 'jar',
    'jpeg', 'jpg', 'lnk', 'log', 'm4a', 'm4b', 'm4p', 'm4v', 'mcd', 'mdb', 'mid', 'mov', 'mp2', 'mp3', 'mp4',
    'mpeg', 'mpg', 'msi', 'mswmm', 'ogg', 'pdf', 'png', 'pps', 'ps', 'psd', 'pst', 'ptb', 'pub', 'qbb',
    'qbw', 'qxd', 'ram', 'rar', 'rm', 'rmvb', 'rtf', 'sea', 'ses', 'sit', 'sitx', 'ss', 'swf', 'tgz', 'thm',
    'tif', 'tmp', 'torrent', 'ttf', 'txt', 'vcd', 'vob', 'wav', 'wma', 'wmv', 'wps', 'xls', 'xpi', 'zip'];

  // Override how files and folders are rendered
  HGrid.Col.Name.itemView = function(row, args) {
    args = args || {};
    var innerContent = [HGrid.Html.fileIcon, sanitized(row.name), HGrid.Html.errorElem].join('');
    return asItem(row, withIndent(row, innerContent, args.indent));
  };

  HGrid.Col.Name.folderView = function(row, args) {
    args = args || {};
    var name = row.name;
    // The + / - button for expanding/collapsing a folder
    var expander;
    if (row._node.children.length > 0 && row.depth > 0 || args.lazyLoad) {
      expander = row._collapsed ? HGrid.Html.expandElem : HGrid.Html.collapseElem;
    } else { // Folder is empty
      expander = '<span></span>';
    }
    // Concatenate the expander, folder icon, and the folder name
    var innerContent = [expander, HGrid.Html.folderIcon, name].join(' ');
    return asItem(row, withIndent(row, innerContent, args.indent));
  };

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



