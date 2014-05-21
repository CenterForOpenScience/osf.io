#
# omdict - Ordered Multivalue Dictionary.
#
# Arthur Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)

import unittest
from itertools import izip, izip_longest, repeat, product

from orderedmultidict.itemlist import itemlist

_unique = object()

class TestItemList(unittest.TestCase):
  def setUp(self):
    self.inits = [
      [], [(0,0)], [(0,0),(0,0),(None,None)], [(0,0),(1,1),(2,2)],
      [(True,False)], [(False,True)], [(object(),object()),(object(),object())],
      [('p','pumps'),('d','dumps')],
      ]
    self.appends = [(0,0), (1,1), (None,None), (True,False), (object(),object())]
  
  def test_init(self):
    for init in self.inits:
      il = itemlist(init)
      assert il.items() == init

  def test_append(self):
    for init in self.inits:
      il = itemlist(init)
      for key, value in self.appends:
        oldsize = len(il)
        newnode = il.append(key, value)
        assert len(il) == oldsize + 1
        assert il[-1] == newnode

  def test_removenode(self):
    for init in self.inits:
      il = itemlist(init)
      for node, key, value in il:
        oldsize = len(il)
        assert node in il
        assert il.removenode(node) == il
        assert len(il) == oldsize - 1
        assert node not in il

  def test_clear(self):
    for init in self.inits:
      il = itemlist(init)
      if len(init) > 0:
        assert bool(il)
      assert il.clear() == il
      assert not il

  def test_items_keys_values_iteritems_iterkeys_itervalues(self):
    for init in self.inits:
      il = itemlist(init)
      iterator = izip(izip(il.items(), il.keys(), il.values()),
                      izip(il.iteritems(), il.iterkeys(), il.itervalues()))
      for (item1,key1,value1), (item2,key2,value2) in iterator:
        assert item1 == item2 and key1 == key2 and value1 == value2

  def test_reverse(self):
    for init in self.inits:
      il = itemlist(init)
      items = il.items()
      items.reverse()
      assert il.reverse() == il
      assert items == il.items()

  def test_len(self):
    for init in self.inits:
      il = itemlist(init)
      assert len(il) == len(init)
      for key, value in self.appends:
        oldsize = len(il)
        il.append(key, value)
        assert len(il) == oldsize + 1

  def test_contains(self):
    for init in self.inits:
      il = itemlist(init)
      for node, key, value in il:
        assert node in il
        assert (key, value) in il

      assert None not in il
      assert _unique not in il
      assert (19283091823,102893091820) not in il

  def test_iter(self):
    for init in self.inits:
      il = itemlist(init)
      for node, key, value in il:
        assert node in il
        assert (key, value) in il

  def test_delitem(self):
    for init in self.inits:
      for index in [0,-1]:
        il = itemlist(init)
        while il:
          node = il[index]
          assert node in il
          del il[index]
          assert node not in il

  def test_nonzero(self):
    for init in self.inits:
      il = itemlist(init)
      if init:
        assert il
        il.clear()
        assert not il
      else:
        assert not il
