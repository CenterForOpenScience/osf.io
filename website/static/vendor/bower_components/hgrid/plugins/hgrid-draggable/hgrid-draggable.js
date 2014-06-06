(function (global, factory) {
  if (typeof define === 'function' && define.amd) {  // AMD/RequireJS
    define(['jquery', 'hgrid'], factory);
  } else if (typeof module === 'object') {  // CommonJS/Node
    module.exports = factory(jQuery, HGrid);
  } else {  // No module system
    factory(jQuery, HGrid);
  }
}(this, function($, HGrid) {

/**
 * hgrid-draggable - Drag and drop support for HGrid
 */
this.Draggable = (function($, HGrid) {
  'use strict';

  /**
   * Default options for the Slick.RowMoveManager constructor
   * @type {Object}
   */
  var rowMoveManagerDefaults = {
    cancelEditOnDrag: true
  };

  /**
   * Default options for Draggable constructor
   * @type {Object}
   */
  var defaults = {
    /*jshint unused: false */

    onDrop: function(event, items, folder) {},
    onDrag: function(event, items) {},
    acceptDrop: function(item, folder, done) {},
    canDrag: function(item) {
      if (item.kind === HGrid.FOLDER) {
        return false;
      }
      return true;
    },

    // Additional options passed to the HGrid.RowMoveManager constructor
    rowMoveManagerOptions: {},
    // Additional options passed to the HGrid.RowSelectionModel constructor
    rowSelectionModelOptions: {}
  };

  /** Public interface **/

  /**
   * Constructor for the HGrid.Draggable plugin.
   *
   * NOTE: This should NOT invoke the `init` method because `init` will be invoked
   * when HGrid#registerPlugin is called.
   */
  function Draggable(options) {
    var self = this;
    self.options = $.extend({}, defaults, options);
    self.rowMoveManager = null;  // Initialized in init
    // The current drag target
    self._folderTarget = null;
  }

  Draggable.prototype.setTarget = function(folder) {
    this._folderTarget = folder;
  };

  // Initialization function called by HGrid#registerPlugin
  Draggable.prototype.init = function(grid) {
    var self = this;
    var data = grid.getData();
    var dataView = grid.getDataView();
    var slickgrid = grid.grid;

    // Set selection model
    var rowSelectionModelOptions = self.options.rowSelectionModelOptions;
    slickgrid.setSelectionModel(new HGrid.RowSelectionModel(rowSelectionModelOptions));

    // Configure the RowMoveManager
    var rowMoveManagerOptions = $.extend(
      {}, rowMoveManagerDefaults, self.options.rowMoveManagerOptions
    );
    self.rowMoveManager = new HGrid.RowMoveManager(rowMoveManagerOptions);

    /** Callbacks **/

    var onBeforeMoveRows = function(event, data) {
      // Prevent moving row before or after itself
      for (var i = 0; i < data.rows.length; i++) {
        if (data.rows[i] === data.insertBefore || data.rows[i] === data.insertBefore - 1) {
          event.stopPropagation();
          grid.removeHighlight();
          return false;
        }
      }
    };

    // TODO(sloria): Test me

    /**
     * Callback executed when rows are moved and dropped into a new location
     * on the grid.
     * @param  {Event} event
     * @param  {Object} args  Object containing information about the event,
     *                        including insertBefore.
     */
    var onMoveRows = function (event, args) {
      grid.removeHighlight();
      var extractedRows = [];
      // indices of the rows to move
      var indices = args.rows;

      var movedItems = args.items;
      var errorFunc = function(error){
        if (error) {
          throw new HGrid.Error(error);
        }
      };

      for (var i = 0, item; item = movedItems[i]; i++) {
        self.options.acceptDrop.call(self, item, self._folderTarget, errorFunc);
      }

      // ID of the folder to transfer the items to
      var parentID = self._folderTarget.id;
      // Copy the moved items, but change the parentID to the target folder's ID
      var newItems = movedItems.map(function(item) {
        var newItem = $.extend({}, item);
        newItem.parentID = parentID;
        // remove depth and _node properties
        // these will be set upon adding the item to the grid
        delete newItem.depth;
        delete newItem._node;
        return newItem;
      });

      // Remove dragged items from grid
      for (var i = 0, item; item = movedItems[i]; i++) {
        grid.removeItem(item.id);
      }
      // Add items at new location
      grid.addItems(newItems);

      slickgrid.resetActiveCell();
      slickgrid.setSelectedRows([]);
      slickgrid.render();
      // invoke user-defined callback
      // TODO(sloria): add target folder as an argument
      self.options.onDrop.call(self, event, movedItems, self._folderTarget);
    };

    var onDragStart = function(event, dd) {
      var cell = slickgrid.getCellFromEvent(event);
      if (!cell) {
        return;
      }

      dd.row = cell.row;
      if (!data[dd.row]) {
        return;
      }

      if (Slick.GlobalEditorLock.isActive()) {
        return;
      }

      event.stopImmediatePropagation();

      var selectedRows = slickgrid.getSelectedRows();

      if (!selectedRows.length || $.inArray(dd.row, selectedRows) === -1) {
        selectedRows = [dd.row];
        slickgrid.setSelectedRows(selectedRows);
      }

      dd.rows = selectedRows;
      dd.count = selectedRows.length;
    };


    /**
     * Given an index, return the correct parent folder to insert an item into.
     * @param  {Number} index
     * @return {Object}     Parent folder object or null
     */
    var getParent = function(index) {
      // First check if the dragged over item is an empty folder
      var prev = dataView.getItemByIdx(index - 1);
      if (prev.kind === HGrid.FOLDER) {
        parent = prev;
      } else{  // The item being dragged over is an item; get it's parent folder
        var insertItem = dataView.getItemByIdx(index);
        parent = grid.getByID(insertItem.parentID);
      }
      return parent;
    };

    var onDragRows = function(event, args) {
      // set the current drag target
      var movedItems = args.items;
      // get the parent of the current item being dragged over
      var parent;
      if (args.insertBefore) {
        parent = getParent(args.insertBefore);
        if (parent) {
          self.setTarget(parent);
          grid.addHighlight(self._folderTarget);
        }
      }
      self.options.onDrag.call(self, event, args.items, parent);
    };

    // TODO: test that this works
    var canDrag = function(item) {
      // invoke user-defined function
      return self.options.canDrag.call(this, item);
    };

    self.rowMoveManager.onBeforeMoveRows.subscribe(onBeforeMoveRows);
    self.rowMoveManager.onMoveRows.subscribe(onMoveRows);
    self.rowMoveManager.onDragRows.subscribe(onDragRows);
    self.rowMoveManager.canDrag = canDrag;

    // Register the slickgrid plugin
    slickgrid.registerPlugin(self.rowMoveManager);

    slickgrid.onDragInit.subscribe(function(event) {
      // prevent grid from cancelling drag'n'drop by default
      event.stopImmediatePropagation;
    });

    slickgrid.onDragStart.subscribe(onDragStart);
  };


  Draggable.prototype.destroy = function() {
    this.rowMoveManager.destroy();
    HGrid.Col.Name.behavior = null;
  };

  HGrid.Draggable = Draggable;
  return Draggable;
}).call(this, jQuery, HGrid);

/**
 * Customized row move manager, modified from slickgrid's rowmovemanger.js (MIT Licensed)
 * https://github.com/mleibman/SlickGrid/blob/master/plugins/slick.rowmovemanager.js
 */
(function ($, HGrid) {

  function RowMoveManager(options) {
    var _grid;
    var _canvas;
    var _dragging;
    var _self = this;
    var _handler = new Slick.EventHandler();
    var _defaults = {
      cancelEditOnDrag: false
    };

    function init(grid) {
      options = $.extend(true, {}, _defaults, options);
      _grid = grid;
      _canvas = _grid.getCanvasNode();
      _handler
        .subscribe(_grid.onDragInit, handleDragInit)
        .subscribe(_grid.onDragStart, handleDragStart)
        .subscribe(_grid.onDrag, handleDrag)
        .subscribe(_grid.onDragEnd, handleDragEnd);
    }

    function destroy() {
      _handler.unsubscribeAll();
    }

    function handleDragInit(e, dd) {
      // prevent the grid from cancelling drag'n'drop by default
      e.stopImmediatePropagation();
    }

    function handleDragStart(e, dd) {
      var cell = _grid.getCellFromEvent(e);

      if (options.cancelEditOnDrag && _grid.getEditorLock().isActive()) {
        _grid.getEditorLock().cancelCurrentEdit();
      }

      if (_grid.getEditorLock().isActive() || !/move|selectAndMove/.test(_grid.getColumns()[cell.cell].behavior)) {
        return false;
      }

      _dragging = true;
      e.stopImmediatePropagation();

      var selectedRows = _grid.getSelectedRows();

      if (selectedRows.length == 0 || $.inArray(cell.row, selectedRows) == -1) {
        selectedRows = [cell.row];
        _grid.setSelectedRows(selectedRows);
      }

      var rowHeight = _grid.getOptions().rowHeight;

      dd.selectedRows = selectedRows;

      var movedItems = dd.selectedRows.map(function(rowIdx) {
        return _grid.getData().getItemByIdx(rowIdx);
      });

      for (var i = 0, item; item = movedItems[i]; i++) {
        if (_self.canDrag(item) === false) {
          return false;
        }
      }

      dd.selectionProxy = $("<div class='slick-reorder-proxy'/>")
          .css("position", "absolute")
          .css("zIndex", "99999")
          .css("width", $(_canvas).innerWidth())
          .css("height", rowHeight * selectedRows.length)
          .appendTo(_canvas);

      dd.guide = $("<div class='slick-reorder-guide'/>")
          .css("position", "absolute")
          .css("zIndex", "99998")
          .css("width", $(_canvas).innerWidth())
          .css("top", -1000)
          .appendTo(_canvas);

      dd.insertBefore = -1;

      _self.onDragRowsStart.notify({
        rows: dd.selectedRows,
        items: movedItems
      });
    }

    function handleDrag(e, dd) {
      if (!_dragging) {
        return;
      }

      e.stopImmediatePropagation();

      var top = e.pageY - $(_canvas).offset().top;
      dd.selectionProxy.css("top", top - 5);

      var insertBefore = Math.max(0, Math.min(Math.round(top / _grid.getOptions().rowHeight), _grid.getDataLength()));

      // The moved data items
      var movedItems = dd.selectedRows.map(function(rowIdx) {
        return _grid.getData().getItemByIdx(rowIdx);
      });
      dd.movedItems = movedItems;

      if (insertBefore !== dd.insertBefore) {
        var eventData = {
          rows: dd.selectedRows,
          insertBefore: insertBefore,
          items: dd.movedItems
        };

        if (_self.onBeforeMoveRows.notify(eventData) === false) {
          dd.guide.css("top", -1000);
          dd.canMove = false;
        } else {
          dd.guide.css("top", insertBefore * _grid.getOptions().rowHeight);
          dd.canMove = true;
        }

        dd.insertBefore = insertBefore;
      }

      _self.onDragRows.notify({
        rows: dd.selectedRows,
        insertBefore: dd.insertBefore,
        items: movedItems
      });
    }

    function handleDragEnd(e, dd) {
      if (!_dragging) {
        return;
      }
      _dragging = false;
      e.stopImmediatePropagation();

      dd.guide.remove();
      dd.selectionProxy.remove();

      if (dd.canMove) {
        var eventData = {
          'rows': dd.selectedRows,
          'items': dd.movedItems,
          'insertBefore': dd.insertBefore
        };
        // TODO:  _grid.remapCellCssClasses ?
        _self.onMoveRows.notify(eventData);
      }
    }

    $.extend(this, {
      'onDragRowsStart': new Slick.Event(),
      'onBeforeMoveRows': new Slick.Event(),
      'onMoveRows': new Slick.Event(),
      'onDragRows': new Slick.Event(),
      /*jshint unused:false */
      'canDrag': function(item) { return true; },
      'init': init,
      'destroy': destroy
    });
  }

  HGrid.RowMoveManager = RowMoveManager;
})(jQuery, HGrid);

/**
 * Customized row selection model, modified from slickgrid's rowselectionmodel.js (MIT Licensed)
 * https://github.com/mleibman/SlickGrid/blob/master/plugins/slick.rowselectionmodel.js
 */
(function ($, HGrid) {


    function RowSelectionModel(options) {
      var _grid;
      var _ranges = [];
      var _self = this;
      var _handler = new Slick.EventHandler();
      var _inHandler;
      var _options;
      var _defaults = {
        selectActiveRow: true
      };

      function init(grid) {
        _options = $.extend(true, {}, _defaults, options);
        _grid = grid;
        _handler.subscribe(_grid.onActiveCellChanged,
          wrapHandler(handleActiveCellChange));
        _handler.subscribe(_grid.onKeyDown,
          wrapHandler(handleKeyDown));
        _handler.subscribe(_grid.onClick,
          wrapHandler(handleClick));
      }

      function destroy() {
        _handler.unsubscribeAll();
      }

      function wrapHandler(handler) {
        return function () {
          if (!_inHandler) {
            _inHandler = true;
            handler.apply(this, arguments);
            _inHandler = false;
          }
        };
      }

      function rangesToRows(ranges) {
        var rows = [];
        for (var i = 0; i < ranges.length; i++) {
          for (var j = ranges[i].fromRow; j <= ranges[i].toRow; j++) {
            rows.push(j);
          }
        }
        return rows;
      }

      function rowsToRanges(rows) {
        var ranges = [];
        var lastCell = _grid.getColumns().length - 1;
        for (var i = 0; i < rows.length; i++) {
          ranges.push(new Slick.Range(rows[i], 0, rows[i], lastCell));
        }
        return ranges;
      }

      function getRowsRange(from, to) {
        var i, rows = [];
        for (i = from; i <= to; i++) {
          rows.push(i);
        }
        for (i = to; i < from; i++) {
          rows.push(i);
        }
        return rows;
      }

      function getSelectedRows() {
        return rangesToRows(_ranges);
      }

      function filterRowsNotInParent(rows) {
        var i, newRows = [];
        var originalRowIndex = rows[rows.length - 1];
        var gridData = _grid.getData();
        var originalRow = gridData.getItem(originalRowIndex);
        if (typeof originalRow !== 'undefined') {
          var originalParent = originalRow.parentID;
          for (i = 0; i < rows.length; i++) {
            var currentItem = gridData.getItem(rows[i]);
            if(currentItem.parentID == originalParent){
              newRows.push(rows[i]);
            }
          }
        }
        return newRows;
      }

      function setSelectedRows(rows) {
        setSelectedRanges(rowsToRanges(filterRowsNotInParent(rows)));
      }

      function setSelectedRanges(ranges) {
        _ranges = ranges;
        _self.onSelectedRangesChanged.notify(_ranges);
      }

      function getSelectedRanges() {
        return _ranges;
      }

      function handleActiveCellChange(e, data) {
        if (_options.selectActiveRow && data.row != null) {
          setSelectedRanges([new Slick.Range(data.row, 0, data.row, _grid.getColumns().length - 1)]);
        }
      }

      function handleKeyDown(e) {
        var activeRow = _grid.getActiveCell();
        if (activeRow && e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey && (e.which == 38 || e.which == 40)) {
          var selectedRows = getSelectedRows();
          selectedRows.sort(function (x, y) {
            return x - y
          });

          if (!selectedRows.length) {
            selectedRows = [activeRow.row];
          }

          var top = selectedRows[0];
          var bottom = selectedRows[selectedRows.length - 1];
          var active;

          if (e.which == 40) {
            active = activeRow.row < bottom || top == bottom ? ++bottom : ++top;
          } else {
            active = activeRow.row < bottom ? --bottom : --top;
          }

          if (active >= 0 && active < _grid.getDataLength()) {
            _grid.scrollRowIntoView(active);
            _ranges = rowsToRanges(getRowsRange(top, bottom));
            setSelectedRanges(_ranges);
          }

          e.preventDefault();
          e.stopPropagation();
        }
      }

      function handleClick(e) {
        var cell = _grid.getCellFromEvent(e);
        if (!cell || !_grid.canCellBeActive(cell.row, cell.cell)) {
          return false;
        }

        if (!_grid.getOptions().multiSelect || (
          !e.ctrlKey && !e.shiftKey && !e.metaKey)) {
          return false;
      }

      var selection = rangesToRows(_ranges);
      var idx = $.inArray(cell.row, selection);

      if (idx === -1 && (e.ctrlKey || e.metaKey)) {
        selection.push(cell.row);
        _grid.setActiveCell(cell.row, cell.cell);
      } else if (idx !== -1 && (e.ctrlKey || e.metaKey)) {
        selection = $.grep(selection, function (o, i) {
          return (o !== cell.row);
        });
        _grid.setActiveCell(cell.row, cell.cell);
      } else if (selection.length && e.shiftKey) {
        var last = selection.pop();
        var from = Math.min(cell.row, last);
        var to = Math.max(cell.row, last);
        selection = [];
        for (var i = from; i <= to; i++) {
          if (i !== last) {
            selection.push(i);
          }
        }
        selection.push(last);
        _grid.setActiveCell(cell.row, cell.cell);
      }

      _ranges = rowsToRanges(filterRowsNotInParent(selection));
      setSelectedRanges(_ranges);
      e.stopImmediatePropagation();

      return true;
    }

    $.extend(this, {
      'getSelectedRows': getSelectedRows,
      'setSelectedRows': setSelectedRows,

      'getSelectedRanges': getSelectedRanges,
      'setSelectedRanges': setSelectedRanges,

      'init': init,
      'destroy': destroy,

      'onSelectedRangesChanged': new Slick.Event()
    });
  }

  HGrid.RowSelectionModel = RowSelectionModel;
})(jQuery, HGrid);

    return Draggable;
}));
