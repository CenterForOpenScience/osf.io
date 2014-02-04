/**
 * Provides the main HGrid class and HGridError.
 * @module HGrid
 */
; // jshint ignore: line
if (typeof jQuery === 'undefined') {
  throw new Error('HGrid requires jQuery to be loaded');
}
(function($, window, document, undefined) {
  'use strict';
  // Exports
  window.HGrid = HGrid;
  window.HGridError = HGridError;

  var DEFAULT_INDENT = 15;
  var ROOT_ID = 'root';
  var ITEM = 'item';
  var FOLDER = 'folder';
  function noop() {}


  /////////////////////
  // Data Structures //
  /////////////////////

  var idCounter = 0; // Ensure unique IDs among trees and leaves
  function getUID() {
    return idCounter++;
  }
  /**
   * A tree node. If constructed with no args, the node is
   * considered a root,
   *
   * ```
   * var root = new HGrid.Tree();
   * root.depth // => 0
   * var subtree = new Tree({name: 'A subtree', kind: 'folder'});
   * root.add(subtree);
   * subtree.depth  // => 1
   * ```
   *
   * @class HGrid.Tree
   * @constructor
   * @param {Object} data Data to attach to the tree
   */
  function Tree(data) {
    if (data === undefined) { // No args passed, it's a root
      this.data = {};
      this.id = ROOT_ID;
      /**
       * @attribute  depth
       * @type {Number}
       */
      this.depth = 0;
      this.dataView = new Slick.Data.DataView({
        inlineFilters: true
      });
    } else {
      this.data = data;
      this.id = data.id ? data.id : getUID();
      // Depth and dataView will be set by parent after being added as a subtree
      this.depth = null;
      this.dataView = null;
    }
    this.children = [];
    this.parentID = null;
  }
  /**
   * Construct a new Tree from either an object or an array of data.
   *
   * Example input:
   * ```
   * [{name: 'Documents', kind: 'folder',
   *  children: [{name: 'mydoc.txt', type: 'item'}]},
   *  {name: 'rootfile.txt', kind: 'item'}
   *  ]
   *  ```
   *
   * @method fromObject
   * @param {Object} data
   * @param {parent} [parent] Parent item.
   *
   */
  Tree.fromObject = function(data, parent, args) {
    args = args || {};
    var tree, children, leaf, subtree;
    // If data is an array, create a new root
    if (Array.isArray(data)) {
      tree = new Tree();
      children = data;
    } else { // data is an object, create a subtree
      children = data.children || [];
      tree = new Tree(data);
      tree.depth = parent.depth + 1;
      tree.dataView = parent.dataView;
      if (args.collapse) {
        // TODO: Hardcoded. Change this when _collapsed and _hidden states
        // are saved on Tree and Leaf objects, and not just on the dataview items
        tree.data._collapsed = true;
      }
    }
    // Assumes nodes have a `kind` property. If `kind` is "item", create a leaf,
    // else create a Tree.
    // TODO: This logic might not be necessary. Could just create a tree node for
    // every item.
    for (var i = 0, len = children.length; i < len; i++) {
      var child = children[i];
      if (child.kind === ITEM) {
        leaf = Leaf.fromObject(child, tree, args);
        tree.add(leaf);
      } else {
        subtree = Tree.fromObject(child, tree, args);
        tree.add(subtree);
      }
    }
    return tree;
  };

  Tree.resetIDCounter = function() {
    idCounter = 0;
  };
  Tree._getCurrentID = function() {
    return idCounter;
  };

  /**
   * Add a component to this node
   * @method  add
   * @param component      Either a Tree or Leaf.
   * @param {Boolean} [updateDataView] Whether to insert the item into the DataView
   */
  Tree.prototype.add = function(component, updateDataView) {
    // Set deptth, parent ID, and dataview
    component.parentID = this.id;
    component.depth = this.depth + 1;
    component.dataView = this.dataView;
    this.children.push(component);
    if (updateDataView) {
      this.insertIntoDataView(component);
    }
    return this;
  };

  /**
   * Get the tree's corresponding item object from the dataview.
   * @method  getItem
   */
  Tree.prototype.getItem = function() {
    return this.dataView.getItemById(this.id);
  };

  /**
   * Sort the tree in place, on a key.
   * @method  sort
   */
  Tree.prototype.sort = function(key, asc) {
    this.children.sort(function(child1, child2) {
      var val1 = child1.data[key],
        val2 = child2.data[key];
      var sign = asc ? 1 : -1;
      var ret = (val1 === val2 ? 0 : (val1 > val2 ? 1 : -1)) * sign;
      if (ret !== 0) {
        return ret;
      }
      return 0;
    });
    for (var i = 0, child; child = this.children[i]; i++) {
      child.sort(key, asc);
    }
    return this;
  };

  // TODO: test me
  Tree.prototype.sortCmp = function(cmp) {
    this.children.sort(cmp);
    for (var i = 0, child; child = this.children[i]; i++) {
      child.sortCmp(key);
    }
    return this;
  };

  /**
   * Computes the index in the DataView where to insert an item, based on
   * the item's parentID property.
   * @private
   */
  function computeAddIdx(item, dataView) {
    var parent = dataView.getItemById(item.parentID);
    if (parent) {
      return dataView.getIdxById(parent.id) + 1;
    }
    return 0;
  }

  Tree.prototype.insertIntoDataView = function(component) {
    var data = component.toData();
    var idx;
    if (Array.isArray(data)) {
      for (var i = 0, len = data.length; i < len; i++) {
        var datum = data[i];
        idx = computeAddIdx(datum, this.dataView);
        this.dataView.insertItem(idx, datum);
      }
    } else { // data is an Object, so component is a leaf
      idx = computeAddIdx(data, this.dataView);
      this.dataView.insertItem(idx, data);
    }
    return this;
  };

  Tree.prototype.ensureDataView = function(dataView) {
    if (!dataView) {
      dataView = this.dataView;
    }
    this.dataView = dataView;
    for (var i = 0, node; node = this.children[i]; i++) {
      node.ensureDataView(dataView);
    }
    return this;
  };

  /**
   * Update the dataview with this tree's data. This should only be called on
   * a root node.
   */
  Tree.prototype.updateDataView = function(onlySetItems) {
    if (!this.dataView) {
      throw new HGridError('Tree does not have a DataView. updateDataView must be called on a root node.');
    }
    if (!onlySetItems) {
      this.ensureDataView();
    }
    this.dataView.beginUpdate();
    this.dataView.setItems(this.toData());
    this.dataView.endUpdate();
    return this;
  };

  /**
   * Convert the tree to SlickGrid-compatible data
   *
   * @param {Array} result Memoized result.
   * @return {Array} Array of SlickGrid data
   */
  Tree.prototype.toData = function(result) {
    // Add this node's data, unless it's a root
    var data = result || [];
    if (this.depth !== 0) {
      var thisItem = $.extend({}, {
        id: this.id,
        parentID: this.parentID,
        _node: this,
        depth: this.depth
      }, this.data);
      data.push(thisItem);
    }
    for (var i = 0, len = this.children.length; i < len; i++) {
      var child = this.children[i];
      child.toData(data);
    }
    return data;
  };

  /**
   * Collapse this and all children nodes, by setting the _collapsed attribute
   * @method  collapse
   * @param {Boolean} hideSelf Whether to hide this node as well
   */
  Tree.prototype.collapse = function(hideSelf, refresh) {
    var item;
    if (!this.isRoot()){
      item = this.getItem();
      // A node can be collapsed but not hidden. For example, if you click
      // on a folder, it should collapse and hide all of its contents, but the folder
      // should still be visible.
      if (hideSelf) {
        item._hidden = true;
      } else {
        item._collapsed = true;
        item._hidden = false;
      }
    }
    // Collapse and hide all children
    for (var i = 0, node; node = this.children[i]; i++) {
      node.collapse(true);
    }
    if (!this.isRoot() && refresh) {
      this.dataView.updateItem(item.id, item); // need to update the item index
    }
    return this;
  };

  /**
   * Performs breadth-first traversal of the tree, executing a function once
   * per node.
   * @method  bfTraverse
   * @param  {Function} fun      Function to execute for each node
   * @param  {Number} maxDepth Max depth to traverse to, or null.
   */
  Tree.prototype.bfTraverse = function(fun, maxDepth) {
    var frontier = new Queue();
    var next = this;
    while (next) {
      if (maxDepth && next.depth > maxDepth) {
        break;
      }
      fun.call(this, next);
      if (next.children.length) {
        // enqueue all children
        for (var i = 0, child; child = next.children[i]; i++){
          frontier.enq(child);
        }
      }
      next = frontier.deq();
    }
    return this;
  };

  /**
   * Collapse all nodes at a certain depth
   * @method  collapseAt
   * @param  {Number} depth   The depth to collapse at
   * @param  {Boolean} refresh Whether to refresh the DataView.
   */
  Tree.prototype.collapseAt = function(depth, refresh) {
    if (depth === 0) {
      return this.collapse(false, refresh);
    }
    this.bfTraverse(function(node) {
      if (node.depth === depth && node instanceof Tree) {  // only collapse trees on the way
        node.collapse(false, true);  // Make sure item is updated
      }
    }, depth);
    if (refresh) {
      this.dataView.refresh();
    }
    return this;
  };

  Tree.prototype.expandAt = function(depth, refresh) {
    if (depth === 0) {
      return this.expand(false, refresh);
    }
    this.bfTraverse(function(node) {
      if (!node.isRoot() && node.depth < depth) {
        node.expand(false, true);  // Make sure item is updated
      }
    }, depth);
    if (refresh) {
      this.dataView.refresh();
    }
    return this;
  };

  Tree.prototype.isHidden = function() {
    return this.getItem()._hidden;
  };

  /**
   * Expand this and all children nodes by setting the item's _collapsed attribute
   * @method  expand
   */
  Tree.prototype.expand = function(notFirst, refresh) {
    var item;
    if (!this.isRoot()){
      item = this.getItem();
      if (!notFirst) {
        item._collapsed = false;
      }
      item._hidden = false;
    }
    // Expand all children
    for (var i = 0, node; node = this.children[i]; i++) {
      if (!item._collapsed) { // Maintain subtree's collapsed state
        node.expand(true);
      }
    }
    if (!this.isRoot() && refresh) {
      this.dataView.updateItem(item.id, item);
    }
    return this;
  };

  Tree.prototype.isRoot = function() {
    return this.depth === 0;
  };

  /**
   * @method isCollapsed
   * @return {Boolean} Whether the node is collapsed.
   */
  Tree.prototype.isCollapsed = function() {
    return Boolean(this.getItem()._collapsed);
  };

  /**
   * Leaf representation
   * @class  HGrid.Leaf
   * @constructor
   */
  function Leaf(data) {
    this.data = data;
    this.id  = data.id ? data.id : getUID();
    this.parentID = null; // Set by parent
    this.depth = null;
    this.children = [];
    this.dataView = null; // Set by parent
  }
  /**
   * Construct a new Leaf from an object.
   * @method  fromObject
   * @param obj
   * @static
   * @return {Leaf} The constructed Leaf.
   */
  Leaf.fromObject = function(obj, parent, args) {
    args = args || {};
    var leaf = new Leaf(obj);
    if (parent) {
      leaf.depth = parent.depth + 1;
      leaf.parentID = parent.id;
      leaf.dataView = parent.dataView;
    }
    if (args.collapse) {
      // TODO: Hardcoded. Change this when _collapsed and _hidden states
      // are saved on Tree and Leaf objects, and not just on the dataview items
      leaf.data._collapsed = true;
    }
    return leaf;
  };

  /**
   * Get the leaf's corresponding item from the dataview.
   * @method  getItem
   */
  Leaf.prototype.getItem = function() {
    return this.dataView.getItemById(this.id);
  };

  /**
   * Collapse this leaf by setting its item's _collapsed property.
   * @method  collapse
   */
   /*jshint unused: false */
  Leaf.prototype.collapse = function(hideSelf, refresh) {
    var item = this.getItem();
    item._collapsed = item._hidden = true;
    return this;
  };

  /**
   * Expand this leaf by setting its item's _collapse property
   * @method  expand
   */
  Leaf.prototype.expand = function() {
    var item = this.getItem();
    item._collapsed = item._hidden = false;
    return this;
  };

  /**
   * Convert the Leaf to SlickGrid data format
   * @method toData
   * @param  {Array} [result] The memoized result
   * @return {Object}        The leaf an item object.
   */
  Leaf.prototype.toData = function(result) {
    var item = $.extend({}, {
      id: this.id,
      parentID: this.parentID,
      _node: this,
      depth: this.depth
    }, this.data);
    if (result) {
      result.push(item);
    }
    return item;
  };

  Leaf.prototype.ensureDataView = function(dataView) {
    if (!dataView) {
      dataView = this.dataView;
    }
    this.dataView = dataView;
    return this;
  };

  Leaf.prototype.sort = noop;

  Leaf.prototype.isRoot = function() {
    return this.depth === 0;
  };

  // An efficient, lightweight queue implementation, adapted from Queue.js by Steven Morley
  function Queue() {
    this.queue = [];
    this.offset = 0;
  }
  Queue.prototype.enq = function(item) {
    this.queue.push(item);
  };
  Queue.prototype.deq = function() {
    if (this.queue.length === 0) {
      return undefined;
    }
    // store item at front of queue
    var item = this.queue[this.offset];
    if (++ this.offset * 2 >= this.queue.length) {
      this.queue = this.queue.slice(this.offset);
      this.offset = 0;
    }
    return item;
  };
  Queue.prototype.isEmpty = function() {
    return this.queue.length === 0;
  };

  ////////////////
  // Formatting //
  ////////////////

  /**
   * Sanitize a value to be displayed as HTML.
   */
  function sanitized(value) {
    return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /**
   * Render a spacer element given an indent value in pixels.
   */
  function makeIndentElem(indent) {
    return '<span class="hg-indent" style="width:' + indent + 'px"></span>';
  }

  /**
   * Adds a span element that indents an item element, given an item.
   * `item` must have a depth property.
   * @param {Object} item
   * @param {String} html The inner HTML
   * @return {String} The rendered HTML
   */
  function withIndent(item, html, indentWidth) {
    indentWidth = indentWidth || DEFAULT_INDENT;
    var indent = item.depth * indentWidth;
    // indenting span
    var spacer = makeIndentElem(indent);
    return spacer + html;
  }

  /**
   * Surrounds HTML with a span with class='hg-item-content' and 'data-id' attribute
   * equal to the item's id
   * @param  {Object} item The item object
   * @param  {string} html The inner HTML
   * @return {String}      The rendered HTML
   */
  function asItem(item, html) {
    var openTag = '<div class="' + HGrid.Html.itemClass + '" data-id="' + item.id + '">';
    var closingTag = '</div>';
    return [openTag, html, closingTag].join('');
  }

  /**
   * Render the html for a button, given an item and buttonDef. buttonDef is an
   * object of the form {text: "My button", cssClass: "btn btn-primary",
   *                     onClick: function(evt, item) {alert(item.name); }}
   * @class  renderButton
   * @private
   */
  function renderButton(buttonDef) {
    var cssClass;
    // For now, buttons are required to have the hg-btn class so that a click
    // event listener can be attacked to them later
    if (buttonDef.cssClass) {
      cssClass = HGrid.Html.buttonClass + ' ' + buttonDef.cssClass;
    } else {
      cssClass = HGrid.Html.buttonClass;
    }
    var action = buttonDef.action || 'noop';
    var openTag = '<button data-hg-action="' + action + '" class="' + cssClass + '">';
    var closingTag = '</button>';
    var html = [openTag, buttonDef.text, closingTag].join('');
    return html;
  }

  function renderButtons(buttonDefs) {
    var renderedButtons = buttonDefs.map(function(btn) {
      var html = renderButton(btn);
      return html;
    }).join('');
    return renderedButtons;
  }

  /**
   * Default rendering function that renders a file item to HTML.
   * @class defaultItemView
   * @param  {Object} item The item data object.
   * @return {String}      HTML for the item.
   */
  function defaultItemView(row, args) {
    args = args || {};
    var innerContent = [HGrid.Html.fileIcon, sanitized(row.name), HGrid.Html.errorElem].join('');
    return asItem(row, withIndent(row, innerContent, args.indent));
  }

  /**
   * Default rendering function that renders a folder row to HTML.
   * @class defaultFolderView
   * @param  {Object} row The folder data object.
   * @return {String}      HTML for the folder.
   */
  function defaultFolderView(row, args) {
    args = args || {};
    var name = sanitized(row.name);
    // The + / - button for expanding/collapsing a folder
    var expander;
    if (row._node.children.length > 0 && row.depth > 0 || args.lazyLoad) {
      expander = row._collapsed ? HGrid.Html.expandElem : HGrid.Html.collapseElem;
    } else { // Folder is empty
      expander = '<span></span>';
    }
    // Concatenate the expander, folder icon, and the folder name
    var innerContent = [expander, HGrid.Html.folderIcon, name, HGrid.Html.errorElem].join(' ');
    return asItem(row, withIndent(row, innerContent, args.indent));
  }

  /**
   * Microtemplating function. Adapted from Riot.js (MIT License).
   */
  var tpl_fn_cache = {};
  var tpl = function(template, data) {
    /*jshint quotmark:false */
    if (!template) {
      return '';
    }
    tpl_fn_cache[template] = tpl_fn_cache[template] || new Function("_",
      "return '" + template
      .replace(/\n/g, "\\n")
      .replace(/\r/g, "\\r")
      .replace(/'/g, "\\'")
      .replace(/\{\{\s*(\w+)\s*\}\}/g, "'+(_.$1?(_.$1+'').replace(/&/g,'&amp;').replace(/\"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;'):(_.$1===0?0:''))+'") + "'"
    );
    return tpl_fn_cache[template](data);
  };

  HGrid.Html = {
    // Expand/collapse button
    expandElem: '<span class="hg-toggle hg-expand"></span>',
    collapseElem: '<span class="hg-toggle hg-collapse"></span>',
    // Icons
    folderIcon: '<i class="hg-folder"></i>',
    fileIcon: '<i class="hg-file"></i>',
    // Placeholder for error messages. Upload error messages will be interpolated here
    errorElem: '&nbsp;<span class="error" data-upload-errormessage></span>',
    // CSS Classes
    buttonClass: 'hg-btn',
    itemClass: 'hg-item-content',
    toggleClass: 'hg-toggle'
  };

  ///////////
  // HGrid //
  ///////////

  // Formatting helpers public interface
  HGrid.Fmt = HGrid.Format = {
    withIndent: withIndent,
    asItem: asItem,
    makeIndentElem: makeIndentElem,
    sanitized: sanitized,
    button: renderButton,
    buttons: renderButtons,
    tpl: tpl
  };

  // Predefined actions
  HGrid.Actions = {
    download: {
      on: 'click',
      callback: function(evt, item) {
        this.options.onClickDownload.call(this, evt, item);
      }
    },
    delete: {
      on: 'click',
      callback: function(evt, item) {
        this.options.onClickDelete.call(this, evt, item);
      }
    },
    upload: {
      on: 'click',
      callback: function(evt, item) {
        this.options.onClickUpload.call(this, evt, item);
      }
    },
    noop: {
      on: 'click',
      callback: noop
    }
  };

  // Predefined column schemas
  HGrid.Col = HGrid.Columns = {
    defaultFolderView: defaultFolderView,
    defaultItemView: defaultItemView,

    // Name field schema
    Name: {
      id: 'name',
      name: 'Name',
      sortkey: 'name',
      cssClass: 'hg-cell',
      folderView: defaultFolderView,
      itemView: defaultItemView,
      sortable: true
    },

    // Actions buttons schema
    ActionButtons: {
      id: 'actions',
      name: 'Actions',
      cssClass: 'hg-cell',
      width: 50,
      sortable: false,
      folderView: function() {
        var buttonDefs = [];
        if (this.options.uploads) {
          buttonDefs.push({
            text: 'Upload',
            action: 'upload'
          });
        }
        if (buttonDefs) {
          return renderButtons(buttonDefs);
        }
        return '';
      },
      itemView: function() {
        var buttonDefs = [{
          text: 'Download',
          action: 'download'
        }, {
          text: 'Delete',
          action: 'delete'
        }];
        return renderButtons(buttonDefs);
      }
    }
  };

  /**
   * Default options object
   * @class  defaults
   */
  var defaults = {
    /**
     * The data for the grid.
     * @property data
     */
    data: null,
    /**
     * Options passed to jQuery.ajax on every request for additional data.
     * @property [ajaxOptions]
     * @type {Object}
     */
    ajaxOptions: {},
    /**
     * Returns the URL where to fetch the contents for a given folder. Enables
     * lazy-loading of data.
     * @param {Object} folder The folder data item.
     * @property {Function} [fetchUrl]
     */
    fetchUrl: null,
    /**
     * Enable uploads (requires DropZone)
     * @property [uploads]
     * @type {Boolean}
     */
    uploads: false,
    /**
     * Array of column schemas
     * @property [columns]
     */
    columns: [HGrid.Columns.Name],
    /**
     * @property  [width] Width of the grid
     */
    width: 600,
    /**
     * Height of the grid div in px or 'auto' (to disable vertical scrolling).*
     * @property [height]
     */
    height: 300,
    /**
     * CSS class applied for a highlighted row.
     * @property [highlightClass]
     * @type {String}
     */
    highlightClass: 'hg-row-highlight',
    /**
     * Width to indent items (in px)*
     * @property indent
     */
    indent: DEFAULT_INDENT,
    /**
     * Additional options passed to Slick.Grid constructor
     * See: https://github.com/mleibman/SlickGrid/wiki/Grid-Options
     * @property [slickgridOptions]
     */
    slickgridOptions: {},
    /**
     * URL to send upload requests to. Can be either a string of a function
     * that receives a data item.
     * Example:
     *  uploadUrl: function(item) {return '/upload/' + item.id; }
     * @property [uploadUrl]
     */
    uploadUrl: null,
    /**
     * Array of accepted file types. Can be file extensions or mimetypes.
     * Example: `['.py', 'application/pdf', 'image/*']
     * @property [acceptedFiles]
     * @type {Array}
     */
    acceptedFiles: null,
    /**
     * Max filesize in Mb.
     * @property [maxFilesize]
     */
    maxFilesize: 256,
    /**
     * HTTP method to use for uploading.
     * Can be either a string or a function that receives the item
     * to upload to and returns the method name.
     */
    uploadMethod: 'POST',
    /**
     * Additional options passed to DropZone constructor
     * See: http://www.dropzonejs.com/
     * @property [dropzoneOptions]
     * @type {Object}
     */
    dropzoneOptions: {},
    /**
     * Callback function executed after an item is clicked.
     * By default, expand or collapse the item.
     * @property [onClick]
     */
    /*jshint unused: false */
    onClick: function(event, item) {},
    onClickDownload: function(event, item, options) {
      this.downloadItem(item, options);
    },
    onClickDelete: function(event, item, options) {
      this.removeItem(item.id);
      this.deleteFile(item, options);
    },
    onClickUpload: function(event, item, options) {
      // Open up a filepicker for the folder
      this.uploadToFolder(item);
    },
    onExpand: function(event, item) {},
    onCollapse: function(event, item) {},
    /**
     * Callback executed after an item is added.
     * @property [onItemAdded]
     */
    onItemAdded: function(item) {},
    // Dragging related callbacks
    onDragover: function(evt, item) {},
    onDragenter: function(evt, item) {},
    onDragleave: function(evt, item) {},
    onDrop: function(event, item) {},
    /**
     *  Called when a column is sorted.
     *  @param {Object} event
     *  @param {Object} column The column definition for the sorted column.
     *  @param {Object} args SlickGrid sorting args.
     */
    onSort: function(event, column, args) {},
    /**
     * Called whenever a file is added for uploaded
     * @param  {Object} file The file object. Has gridElement and gridItem bound to it.
     * @param  {Object} item The added item
     */
    uploadAdded: function(file, item) {},
    /**
     * Called whenever a file gets processed.
     * @property {Function} [uploadProcessing]
     */
    /*jshint unused: false */
    uploadProcessing: function(file, item) {
      // TODO: display Cancel upload button text?
    },
    /**
     * Called whenever an upload error occurs
     * @property [uploadError]
     * @param  {Object} file    The HTML file object
     * @param {String} message Error message
     * @param {Object} item The placeholder item that was added to the grid for the file.
     */
    /*jshint unused: false */
    uploadError: function(file, message, item) {
      // The row element for the added file is stored on the file object
      var $rowElem = $(file.gridElement);
      var msg;
      if (typeof message !== 'string' && message.error) {
        msg = message.error;
      } else {
        msg = message;
      }
      // Show error message in any element within the row
      // that contains 'data-upload-errormessage'
      $rowElem.find('[data-upload-errormessage]').each(function(i) {
        this.textContent = msg;
      });
      return this;
    },
    /**
     * Called whenever upload progress gets updated.
     * @property [uploadProgress]
     * @param  {Object} file      the file object
     * @param  {Number} progress  Percentage (0-100)
     * @param  {Number} bytesSent
     * @param  {The data item element} item
     */
    /*jshint unused: false */
    uploadProgress: function(file, progress, bytesSent, item) {
      // Use the row as a progress bar
      var $row = $(file.gridElement);
      $row.width(progress + '%');
    },
    /**
     * Called whenever an upload is finished successfully
     * @property [uploadSuccess]
     */
    /*jshint unused: false */
    uploadSuccess: function(file, item) {},
    /**
     * Called when an upload completes (whether it is successful or not)
     * @property [uploadComplete]
     */
    uploadComplete: function(file, item) {},
    /**
     * Called before a file gets uploaded. If `done` is called with a string argument,
     * An error is thrown with the message. If `done` is called with no arguments,
     * the file is accepted.
     * @property [uploadAccept]
     * @param  {Object} file   The file object
     * @param  {Object} folder The folder item being uploaded to
     * @param  {Function} done Called to either accept or reject a file.
     */
    uploadAccept: function(file, folder, done) {
      return done();
    },
    /**
     * Returns the url where to download and item
     * @param  {Object} row The row object
     * @return {String} The download url
     */
    downloadUrl: function(item) {},
    deleteUrl: function(item) {},
    deleteMethod: function(item) {},

    listeners: [],
    /**
     * Additional initialization. Useful for adding listeners.
     * @property {Function} init
     */
    init: function() {},
    // CSS Selector for search input box
    searchInput: null,
    /**
     * Search filter that returns true if an item should be displayed in the grid.
     * By default, items will be searched by name (case insensitive).
     * @param  {Object} item A data item
     * @param {String} searchText The current text value in the search input box.
     * @return {Boolean}      Whether or not to display an item.
     */
    searchFilter: function (item, searchText) {
      return item.name.toLowerCase().indexOf(searchText) !== -1;
    },
    /**
     * Function that determines whether a folder can be uploaded to.
     */
    canUpload: function(folder) {
      return true;
    },
    /**
     * Called when a user tries to upload to a folder they don't have permission
     * to upload to. This is called before adding a file to the upload queue.
     */
    uploadDenied: function(folder) {}
  };

  HGrid._defaults = defaults;
  // Expose data structures via the HGrid namespace
  HGrid.Tree = Tree;
  HGrid.Leaf = Leaf;
  HGrid.Queue = Queue;

  // Constants
  HGrid.ROOT_ID = ROOT_ID;
  HGrid.FOLDER = FOLDER;
  HGrid.ITEM = ITEM;

  /**
   * Custom Error for HGrid-related errors.
   *
   * @class  HGridError
   * @constructor
   */
  function HGridError(message) {
    this.name = 'HGridError';
    this.message = message || '';
  }
  HGridError.prototype = new Error();

  /**
   * Construct an HGrid.
   *
   * @class  HGrid
   * @constructor
   * @param {String} element CSS selector for the grid.
   * @param {Object} options
   */
  function HGrid(selector, options) {
    var self = this;
    self.selector = selector;
    self.element = $(selector);
    // Merge defaults with options passed in
    self.options = $.extend({}, defaults, options);
    self.grid = null; // Set upon calling _initSlickGrid()
    self.dropzone = null; // Set upon calling _initDropzone()
    if (self.options.searchInput) {
      var $searchInput = $(self.options.searchInput);
      if ($searchInput.length) {
        self.searchInput = $searchInput;
      } else {
        throw new HGridError('Invalid selector for searchInput.');
      }
    } else {
      self.searchInput = null;
    }
    if (typeof self.options.data === 'string') { // data is a URL, get the data asynchronously
      self.getFromServer(self.options.data, function(data, error) {
          self._initData(data);
          self.init();
        }
      );
    } else { // data is an object
      self._initData(self.options.data);
      self.init();
    }
  }

  /**
   * Collapse all folders
   * @return {[type]} [description]
   */
  HGrid.prototype.collapseAll = function() {
    this.tree.collapseAt(1, true);
  };

  /**
   * Helper for retrieving JSON data usin AJAX.
   * @method  getFromServer
   * @param {String} url
   * @param {Function} done Callback that receives the JSON data and an
   *                        error if there is one.
   * @return {jQuery xhr} The xhr object returned by jQuery.ajax.
   */
  HGrid.prototype.getFromServer = function(url, done) {
    var self = this;
    var ajaxOpts = $.extend({}, {
      url: url,
      contentType: 'application/json',
      dataType: 'json',
      success: function(json) {
        done && done.call(self, json);
      },
      error: function(xhr, textStatus, error) {
        done && done.call(self, null, error, textStatus);
      }
    }, self.options.ajaxOptions);
    return $.ajax(ajaxOpts);
  };

  HGrid.prototype._initData = function(data) {
    var self = this;
    if (data) {
      // Tree.fromObject expects an Array, but `data` might be an array or an
      // object with `data' property
      if (Array.isArray(data)) {
        self.tree = Tree.fromObject(data);
      } else {
        self.tree = Tree.fromObject(data.data);
      }
      self.tree.updateDataView(); // Sync Tree with its wrapped dataview
    } else {
      self.tree = new Tree();
    }
    return self;
  };

  HGrid.prototype.init = function() {
    this.setHeight(this.options.height)
      .setWidth(this.options.width)
      ._initSlickGrid()
      ._initDataView();

    if (this.options.uploads) {
      if (typeof Dropzone === 'undefined') {
        throw new HGridError('uploads=true requires DropZone to be loaded');
      }
      this._initDropzone();
    }
    // Attach the listeners last, after this.grid and this.dropzone are set
    this._initListeners();
    // Collapse all top-level folders if lazy-loading
    if (this.isLazy()) {
      this.collapseAll();
    }
    this.options.init.call(this);
    return this;
  };

  HGrid.prototype.setHeight = function(height) {
    if (height === 'auto') {
      this.options.slickgridOptions.autoHeight = true;
    } else {
      this.element.css('height', height);
    }
    return this;
  };

  // TODO: always update column widths after setting width.
  HGrid.prototype.setWidth = function(width) {
    this.element.css('width', width);
    return this;
  };

  // TODO: test me
  // HGrid folderView and itemView (in column def) => SlickGrid Formatter
  HGrid.prototype.makeFormatter = function(folderView, itemView, args) {
    var self = this,
      view;
    var formatter = function(row, cell, value, colDef, item) {
      var rendererArgs = {
        colDef: colDef,
        row: row,
        cell: cell,
        indent: args.indent,
        lazyLoad: self.isLazy()
      };
      if (item.kind === FOLDER) {
        view = folderView;
      } else {
        view = itemView;
      }
      if (typeof view === 'function') {
        return view.call(self, item, rendererArgs); // Returns the rendered HTML
      }
      // Use template
      return HGrid.Format.tpl(view, item);
    };
    return formatter;
  };

  // Hgrid column schemas => Slickgrid columns
  HGrid.prototype._makeSlickgridColumns = function(colSchemas) {
    var self = this;
    var columns = colSchemas.map(function(col) {
      if (!('formatter' in col)) {
        // Create the formatter function from the columns definition's
        // "folderView" and "itemView" properties
        col.formatter = self.makeFormatter.call(self, col.folderView,
          col.itemView, {
            indent: self.options.indent
          });
      }
      if ('text' in col) { // Use 'text' instead of 'name' for column header text
        col.name = col.text;
      }
      return col;
    });
    return columns;
  };

  var requiredSlickgridOptions = {
    editable: false,
    asyncEditorLoading: false,
    enableCellNavigation: false,
    enableColumnReorder: false, // column reordering requires jquery-ui.sortable
    forceFitColumns: true,
    fullWidthRows: true
  };

  /**
   * Constructs a Slick.Grid and Slick.Data.DataView from the data.
   * Sets this.grid.
   * @method  _initSlickGrid
   * @private
   */
  HGrid.prototype._initSlickGrid = function() {
    var self = this;
    // Convert column schemas to Slickgrid column definitions
    var columns = self._makeSlickgridColumns(self.options.columns);
    var options = $.extend({}, requiredSlickgridOptions, self.options.slickgridOptions);
    self.grid = new Slick.Grid(self.element.selector, self.tree.dataView,
      columns,
      options);
    return self;
  };

  HGrid.prototype.removeHighlight = function() {
    this.element.find('.' + this.options.highlightClass)
      .removeClass(this.options.highlightClass);
    return this;
  };

  /**
   * Get the row element for an item, given its id.
   * @method  getRowElement
   */
  HGrid.prototype.getRowElement = function(id) {
    if (typeof id === 'object') {
      id = id.id;
    }
    return this.grid.getCellNode(this.getDataView().getRowById(id), 0).parentNode;
  };

  HGrid.prototype.addHighlight = function(item) {
    this.removeHighlight();
    var $rowElement;
    if (item && item.kind === FOLDER) {
      $rowElement = $(this.getRowElement(item.id));
    } else {
      $rowElement = $(this.getRowElement(item.parentID));
    }
    if ($rowElement) {
      $rowElement.addClass(this.options.highlightClass);
    }
    return this;
  };

  /**
   * SlickGrid events that the grid subscribes to. Mostly just delegates to one
   * of the callbacks in `options`.
   * For each funcion, `this` refers to the HGrid object.
   * @attribute slickEvents
   */
  HGrid.prototype.slickEvents = {
    'onClick': function(evt, args) {
      var item = this.getDataView().getItem(args.row);
      // Expand/collapse item
      if (this.canToggle(evt.target)) {
        this.toggleCollapse(item, evt);
      }
      this.options.onClick.call(this, evt, item);
      return this;
    },
    'onCellChange': function(evt, args) {
      this.getDataView().updateItem(args.item.id, args.item);
      return this;
    },
    'onMouseLeave': function(evt, args) {
      this.removeHighlight();
    },
    'onSort': function(evt, args) {
      var col = args.sortCol; // column to sort
      var key = col.field || col.sortkey; // key to sort on
      if (!key) {
        throw new HGridError('Sortable column does not define a `sortkey` to sort on.');
      }
      this.tree.sort(key, args.sortAsc);
      this.tree.updateDataView(true);
      this.options.onSort.call(this, evt, col, args);
    }
  };

  HGrid.prototype.getItemFromEvent = function(evt) {
    var cell = this.grid.getCellFromEvent(evt);
    if (cell) {
      return this.getDataView().getItem(cell.row);
    } else {
      return null;
    }
  };

  HGrid.prototype.uploadToFolder = function(item) {
    this.currentTarget = item;
    this.setUploadTarget(item);
    this.dropzone.hiddenFileInput.click();
  };

  // TODO: untested
  HGrid.prototype.downloadItem = function(item) {
    var url;
    if (typeof this.options.downloadUrl === 'function') {
      url = this.options.downloadUrl(item);
    } else {
      url = this.options.downloadUrl;
    }
    if (url) {
      window.location = url;
    }
    return this;
  };

  /**
   * Send a delete request to an item's download URL.
   */
  // TODO: untested
  HGrid.prototype.deleteFile = function(item, ajaxOptions) {
    var url, method;
    // TODO: repetition here
    if (typeof this.options.deleteUrl === 'function') {
      url = this.options.deleteUrl(item);
    } else {
      url = this.options.deleteUrl;
    }
    if (typeof this.options.deleteMethod === 'function') {
      method = this.options.deleteMethod(item);
    } else {
      method = this.options.deleteMethod;
    }
    var options = $.extend({}, {
      url: url,
      type: method
    }, ajaxOptions);
    var promise = null;
    if (url) {
      promise = $.ajax(options);
    }
    return promise;
  };

  HGrid.prototype.currentTarget = null; // The item to upload to

  /**
   * Update the dropzone object's options dynamically. Lazily updates the
   * upload url, method, etc.
   * @method  setUploadTarget
   */
  HGrid.prototype.setUploadTarget = function(item) {
    var self = this;
    // if upload url or upload method is a function, call it, passing in the target item,
    // and set dropzone to upload to the result
    if (self.currentTarget) {
      if (typeof this.options.uploadUrl === 'function') {
        self.dropzone.options.url = self.options.uploadUrl.call(self, item);
      }
      if (typeof self.options.uploadMethod === 'function') {
        self.dropzone.options.method = self.options.uploadMethod.call(self, item);
      }
      if (this.options.uploadAccept) {
        // Override dropzone accept callback. Just calls options.uploadAccept with the right params
        this.dropzone.options.accept = function(file, done) {
          return self.options.uploadAccept.call(self, file, item, done);
        };
      }
    }
  };

  HGrid.prototype.canUpload = function(item) {
    return Boolean(item && this.options.canUpload(item));
  };

  HGrid.prototype.denyUpload = function(targetItem) {
    // Need to throw an error to prevent dropzone's sequence of callbacks from firing
    this.options.uploadDenied.call(this, targetItem);
    throw new HGridError('Upload permission denied.');
  };

  HGrid.prototype.validateTarget = function(targetItem) {
    if (!this.canUpload(targetItem)) {
      return this.denyUpload(targetItem);
    } else {
      return targetItem;
    }
  };

  /**
   * DropZone events that the grid subscribes to.
   * For each function, `this` refers to the HGrid object.
   * These listeners are responsible for any setup that needs to occur before executing
   * the callbacks in `options`, e.g., adding a new row item to the grid, setting the
   * current upload target, adding special CSS classes
   * and passing necessary arguments to the options callbacks.
   * @attribute  dropzoneEvents
   * @type {Object}
   */
  HGrid.prototype.dropzoneEvents = {
    drop: function(evt) {
      this.removeHighlight();
      this.validateTarget(this.currentTarget);
      // update the dropzone options, eg. dropzone.options.url
      this.setUploadTarget(this.currentTarget);
      this.options.onDrop.call(this, evt, this.currentTarget);
    },
    dragleave: function(evt) {
      this.removeHighlight();
      var item = this.getItemFromEvent(evt);
      this.options.onDragleave.call(this, evt, item);
    },
    // Set the current upload target upon dragging a file onto the grid
    dragenter: function(evt) {
      var item = this.getItemFromEvent(evt);
      if (item) {
        if (item.kind === FOLDER) {
          this.currentTarget = item;
        } else {
          this.currentTarget = this.getByID(item.parentID);
        }
      }
      this.options.onDragenter.call(this, evt, item);
    },
    dragover: function(evt) {
      var currentTarget = this.currentTarget;
      var item = this.getItemFromEvent(evt);
      if(this.canUpload(currentTarget)) {
        if (currentTarget) {
          this.addHighlight(currentTarget);
        }
      }
      this.options.onDragover.call(this, evt, item);
    },
    dragend: function(evt) {
      this.removeHighlight();
    },
    // When a file is added, set currentTarget (the folder item to upload to)
    // and bind gridElement (the html element for the added row) and gridItem
    // (the added item object) to the file object
    addedfile: function(file) {
      var currentTarget = this.currentTarget;
      this.validateTarget(currentTarget);
      var addedItem;
      if (this.canUpload(currentTarget)){
        // Add a new row
        addedItem = this.addItem({
          name: file.name,
          kind: HGrid.ITEM,
          parentID: currentTarget.id
        });
        var rowElem = this.getRowElement(addedItem.id),
          $rowElem = $(rowElem);
        // Save the item data and HTML element on the file object
        file.gridItem = addedItem;
        file.gridElement = rowElem;
        $rowElem.addClass('hg-upload-started');
      }
      this.options.uploadAdded.call(this, file, file.gridItem);
      return addedItem;
    },
    thumbnail: noop,
    // Just delegate error function to options.uploadError
    error: function(file, message) {
      var $rowElem = $(file.gridElement);
      $rowElem.addClass('hg-upload-error').removeClass('hg-upload-processing');
      return this.options.uploadError.call(this, file, message, file.gridItem);
    },
    processing: function(file) {
      $(file.gridElement).addClass('hg-upload-processing');
      this.options.uploadProcessing.call(this, file, file.gridItem);
      return this;
    },
    uploadprogress: function(file, progress, bytesSent) {
      return this.options.uploadProgress.call(this, file, progress, bytesSent, file.gridItem);
    },
    success: function(file) {
      $(file.gridElement).addClass('hg-upload-success')
        .removeClass('hg-upload-processing');
      return this.options.uploadSuccess.call(this, file, file.gridItem);
    },
    complete: function(file) {
      return this.options.uploadComplete.call(this, file, file.gridItem);
    }
  };

  /**
   * Wires up all the event handlers.
   * @method  _initListeners
   * @private
   */
  HGrid.prototype._initListeners = function() {
    var self = this,
      callbackName, fn;
    // Wire up all the slickgrid events
    for (callbackName in self.slickEvents) {
      fn = self.slickEvents[callbackName].bind(self); // make `this` object the grid
      self.grid[callbackName].subscribe(fn);
    }

    if (this.options.uploads) {
      // Wire up all the dropzone events
      for (callbackName in self.dropzoneEvents) {
        fn = self.dropzoneEvents[callbackName].bind(self);
        self.dropzone.on(callbackName, fn);
      }
    }

    // Attach extra listeners from options.listeners
    var userCallback = function(evt) {
      var row = self.getItemFromEvent(evt);
      return evt.data.listenerObj.callback.call(self, evt, row);
    };
    for (var i = 0, listener; listener = this.options.listeners[i]; i++) {
      self.element.on(listener.on, listener.selector, {
        listenerObj: listener
      }, userCallback);
    }
    this.attachActionListeners();

    if (self.searchInput) {
      self.searchInput.keyup(function (e) {
        self._searchText = this.value;
        self.getDataView().refresh();
        self.grid.invalidate();
        self.grid.render();
      });
    }
  };

  /**
   * Attaches event listeners based on the actions defined in HGrid.Actions.
   * For example, if a "spook" action might be defined like so
   *
   * ```
   * HGrid.Actions['spook'] = {
   *   on: 'click',
   *   callback: function(evt, row) {
   *     alert('Boo!')
   *   }
   * };
   *```
   * and a button is created using HGrid.Format.button
   * ```
   * ...
   * Hgrid.Format.button(item, {text: 'Spook', action: 'spook'})
   * ```
   * a "click" event listener will automatically be added to the button with
   * the defined callback.
   *
   */
  HGrid.prototype.attachActionListeners = function() {
    var self = this;
    // Register any new actions;
    $.extend(HGrid.Actions, self.options.actions);
    // This just calls the action's defined callback
    var actionCallback = function(evt) {
      var row = self.getItemFromEvent(evt);
      evt.data.actionObj.callback.call(self, evt, row);
    };
    for (var actionName in HGrid.Actions) {
      var actionDef = HGrid.Actions[actionName];
      this.element.on(actionDef.on, '[data-hg-action="' + actionName + '"]', {
        actionObj: actionDef
      }, actionCallback);
    }
    return this;
  };

  /**
   * Filter used by SlickGrid for searching and expanding/collapsing items.
   * Receives an item and returns true if the item should be displayed in the
   * grid.
   *
   * @class  hgFilter
   * @private
   * @returns {Boolean} Whether to display the item or not.
   */
  function hgFilter(item, args) {
    var visible;

    if (args.grid && args.grid._searchText) {
      item.depth = 0;  // Show search results without indent
      // Use search filter function
      visible =  args.searchFilter.call(args.grid, item, args.grid._searchText);
    } else {
      item.depth = item._node.depth;  // Restore indent
      visible = !item._hidden;  // Hide collapsed elements
    }

    return visible;
  }
  // Expose collapse filter for testing purposes
  HGrid._hgFilter = hgFilter;

  /**
   * Sets up the DataView with the filter function. Must be executed after
   * initializing the Slick.Grid because the filter function needs access to the
   * data.
   * @method  _initDataView
   * @private
   */
  HGrid.prototype._initDataView = function() {
    var self = this;
    var dataView = this.getDataView();
    dataView.beginUpdate();
    dataView.setFilterArgs({ grid: self, searchFilter: self.options.searchFilter });
    dataView.setFilter(hgFilter);
    dataView.endUpdate();
    dataView.onRowCountChanged.subscribe(function(event, args) {
      self.grid.updateRowCount();
      self.grid.render();
    });

    dataView.onRowsChanged.subscribe(function(event, args) {
      self.grid.invalidateRows(args.rows);
      self.grid.render();
    });
    return this;
  };

  var requiredDropzoneOpts = {
    addRemoveLinks: false,
    previewTemplate: '<div></div>' // just a dummy template because dropzone requires it
  };

  /**
   * Builds a new DropZone object and attaches it the "dropzone" attribute of
   * the grid.
   * @method  _initDropZone
   * @private
   */
  HGrid.prototype._initDropzone = function() {
    var uploadUrl, uploadMethod;
    if (typeof this.options.uploadUrl === 'string') {
      uploadUrl = this.options.uploadUrl;
    } else { // uploadUrl is a function, so compute the url lazily;
      uploadUrl = '/'; // placeholder
    }
    if (typeof this.options.uploadMethod === 'string') {
      uploadMethod = this.options.uploadMethod;
    } else { // uploadMethod is a function, so compute the upload url lazily
      uploadMethod = 'POST'; // placeholder
    }
    // Build up the options object, combining the HGrid options, required options,
    // and additional options
    var dropzoneOptions = $.extend({}, {
        url: uploadUrl,
        // Dropzone expects comma separated list
        acceptedFiles: this.options.acceptedFiles ?
          this.options.acceptedFiles.join(',') : null,
        maxFilesize: this.options.maxFilesize,
        method: uploadMethod
      },
      requiredDropzoneOpts,
      this.options.dropzoneOptions);
    this.dropzone = new Dropzone(this.selector, dropzoneOptions);
    return this;
  };

  HGrid.prototype.destroy = function() {
    this.element.html('');
    this.grid.destroy();
    if (this.dropzone) {
      this.dropzone.destroy();
    }
  };

  /**
   * Return the data as an array.
   *
   * @method  getData
   * @return {Array} Array of data items in the DataView.
   */
  HGrid.prototype.getData = function() {
    return this.getDataView().getItems();
  };

  /**
   * Get a datum by it's ID.
   */
  HGrid.prototype.getByID = function(id) {
    var dataView = this.getDataView();
    return dataView.getItemById(id);
  };

  /**
   * Return the grid's underlying DataView.
   * @method  getDataView
   * @return {Slick.Data.DataView}
   */
  HGrid.prototype.getDataView = function() {
    return this.grid.getData();
  };

  HGrid.prototype.getRefreshHints = function (item) {
    var ignoreBefore = this.getDataView().getRowById(item.id);
    var hints = {
      expand: {
        isFilterNarrowing: false, isFilterExpanding: true, ignoreDiffsBefore: ignoreBefore
      },
      collapse: {
        isFilterNarrowing: true, isFilterExpanding: false, ignoreDiffsBefore: ignoreBefore
      }
    };
    return hints;
  };

  HGrid.prototype.isLazy = function() {
    return Boolean(this.options.fetchUrl);  // Assume lazy loading is enabled if fetchUrl is defined
  };

  HGrid.prototype._lazyLoad = function(item) {
    var self = this;
    var url = self.options.fetchUrl(item);
    if (url !== null) {
      return self.getFromServer(url, function(newData, error) {
        if (!error) {
          self.addData(newData, item.id);
          item._node._loaded = true; // Add flag to make sure data are only fetched once.
        } else {
          throw new HGridError('Could not fetch data from url: "' + url + '". Error: ' + error);
        }
      });
    }
    return false;
  };

  /**
   * Expand an item. Updates the dataview.
   * @method  expandItem
   * @param  {Object} item
   */
  HGrid.prototype.expandItem = function(item, evt) {
    var self = this;
    item = typeof item === 'object' ? item : self.getByID(item);
    var node = self.getNodeByID(item.id);
    item._node.expand();
    if (self.isLazy() && !node._loaded) {
      this._lazyLoad(item);
    }
    var dataview = self.getDataView();
    var hints = self.getRefreshHints(item).expand;
    dataview.setRefreshHints(hints);
    self.getDataView().updateItem(item.id, item);
    self.options.onExpand.call(self, evt, item);
    return self;
  };

  /**
   * Collapse an item. Updates the dataview.
   * @method  collapseItem
   * @param  {Object} item
   */
  HGrid.prototype.collapseItem = function(item, evt) {
    item = typeof item === 'object' ? item : this.getByID(item);
    item._node.collapse();
    var dataview = this.getDataView();
    var hints = this.getRefreshHints(item).collapse;
    dataview.setRefreshHints(hints);
    dataview.updateItem(item.id, item);
    this.options.onCollapse.call(this, evt, item);
    return this;
  };

  HGrid.prototype.updateItem = function(item) {
    return this.getDataView().updateItem(item.id, item);
  };

  HGrid.prototype.isCollapsed = function(item) {
    return Boolean(item._collapsed);
  };

  HGrid.prototype.canToggle = function(elem) {
    return $(elem).hasClass(HGrid.Html.toggleClass);
  };

  /**
   * Add an item to the grid.
   * @method  addItem
   * @param {Object} item Object with `name`, `kind`, and `parentID`.
   *                      If parentID is not specified, the new item is added to the root node.
   *                      Example:
   *                      `{name: 'New Folder', kind: 'folder', parentID: 123}`
   * @return {Object} The added item.
   */
  HGrid.prototype.addItem = function(item) {
    var node, parentNode;
    // Create a new node for the item
    if (item.kind === HGrid.FOLDER) {
      node = new HGrid.Tree(item);
    } else {
      node = new HGrid.Leaf(item);
    }
    if (item.parentID == null) {
      parentNode = this.tree;
    } else {
      parentNode = this.getNodeByID(item.parentID);
    }
    parentNode.add(node, true);
    var newItem = this.getByID(node.id);
    this.options.onItemAdded.call(this, newItem);
    return newItem;
  };

  /**
   * Add multiple items.
   *
   * Only one refresh is made to the grid after adding all the items.
   * @param {Array} items Array of items with "name", "kind", and "parentID".
   */
  // FIXME: This method is slow, because the DataView's idx:id map needs to be updated
  // on every insert
  HGrid.prototype.addItems = function(items) {
    var self = this;
    this.batchUpdate(function() {
      for (var i = 0, len = items.length; i < len; i++) {
        var item = items[i];
        self.addItem(item);
      }
    });
    return this;
  };

  HGrid.prototype.batchUpdate = function(func) {
    this.getDataView().beginUpdate();
    func.call(this);
    this.getDataView().endUpdate();
  };


  /**
   * Add a new grid column
   * @method  addColumn
   * Example:
   * ```
   * grid.addColumn({id: 'size', name: 'File Size', field: 'filesize', width: 50})
   * ```
   * @param {Object} colSpec Column specification. See
   *                         https://github.com/mleibman/SlickGrid/wiki/Column-Options
   */
  HGrid.prototype.addColumn = function(colSpec) {
    var columns = this.grid.getColumns();
    columns.push(colSpec);
    this.grid.setColumns(columns);
    return this;
  };

  /**
   * Remove a data item by id.
   * @method  removeItem
   * @param  {Number} id ID of the datum to remove.
   * @return {Object}    The removed item
   */
  HGrid.prototype.removeItem = function(id) {
    var item = this.getByID(id);
    this.getDataView().deleteItem(id);
    return item;
  };

  /**
   * Return a HGrid.Tree or HGrid.Leaf node given an id.
   * @param {Number} id
   * @return {HGrid.Tree} The Tree or Leaf with the id.
   */
  HGrid.prototype.getNodeByID = function(id) {
    if (id === HGrid.ROOT_ID || id == null) {
      return this.tree;
    }
    var item = this.getByID(id);
    return item._node;
  };

  /**
   * Toggle an item's collapsed/expanded state.
   * @method  toggleCollapse
   * @param  {item} item A folder item
   */
  HGrid.prototype.toggleCollapse = function(item, event) {
    if (item) {
      if (this.isCollapsed(item)) {
        this.expandItem(item, event);
      } else {
        this.collapseItem(item, event);
      }
    }
    return this;
  };

  /**
   * Add more hierarchical data. The `data` param takes the same form as the
   * input data.
   * @param  data    Hierarchical data to add
   * @param {Number} parentID ID of the parent node to add the data to
   */
  HGrid.prototype.addData = function(data, parentID) {
    var self = this;
    var tree = this.getNodeByID(parentID);
    var toAdd;
    if (Array.isArray(data)) {
      toAdd = data;
    } else { // Data is an object with a `data` property
      toAdd = data.data;
    }
    for (var i = 0, datum; datum = toAdd[i]; i++) {
      var node;
      if (datum.kind === HGrid.FOLDER) {
        var args = {collapse: self.isLazy()};
        node = Tree.fromObject(datum, tree, args);
      } else {
        node = Leaf.fromObject(datum, tree);
      }
      tree.add(node, true); // ensure dataview is updated
    }
    return this;
  };

  $.fn.hgrid = function(options) {
    this.each(function() {
      if (!this.id) { // Must have ID because SlickGrid requires a selector
        throw new HGridError('Element must have an ID if initializing HGrid with jQuery');
      }
      var selector = '#' + this.id;
      return new HGrid(selector, options);
    });
  };

})(jQuery, window, document);
