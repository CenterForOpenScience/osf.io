#
# omdict - Ordered Multivalue Dictionary.
#
# Arthur Grunseid
# grunseid.com
# grunseid@gmail.com
#
# License: Build Amazing Things (Unlicense)

import unittest
try:
  from collections import OrderedDict as odict # Python 2.7+.
except ImportError:
  from ordereddict import OrderedDict as odict # Python 2.4-2.6.
from itertools import izip, izip_longest, repeat, product

from orderedmultidict.orderedmultidict import omdict

_unique = object()

# Utility list subclass to expose items() and iteritems() methods on basic
# lists. This provides a common iteration interface for lists and dictionaries
# for looping through their items without having to test for and maintain two
# separate bodies, one for lists and one for dictionaries.
#
# So instead of requiring two bodies, one for lists and one for dicts
#
#  lists = [[(1,1),(2,2)]]
#  dicts = [{1:1,2:2}]
#  for lst in lists:
#    lst == ...
#  for dic in dicts:
#    dic.items() == ...
#
# list and dictionary looping bodies can be merged with itemlist
#
#  itemlist = [itemlist([(1,1),(2,2)]), {1:1,2:2}]
#  for ilist in itemlist:
#    ilist.items() == ...
#
class itemlist(list):
  def items(self):
    return self
  def iteritems(self):
    return iter(self)


class TestOmdict(unittest.TestCase):
  def setUp(self):
    self.inits = [
      {}, {1:1}, {1:1,2:2,3:3}, {None:None}, {None:None,1:1,2:2}, {False:False},
      ]
    self.inits += map(itemlist, [
      [], [(1,1)], [(1,1),(2,2)], [(1,1),(2,2),(1,1)],
      [(1,1),(1,1),(1,1)], [(None,None),(None,None)],
      [(False,False)],
      [(None,1),(1,None),(None,None),(None,1),(1,None)],
      ])

    # Updates to test update() and updateall().
    self.updates = [{}, {7:7}, {7:7,8:8,9:9}, {None:None}, {1:1,2:2}]
    self.updates += map(itemlist, [
      [], [(7,7)], [(7,7),(8,8),(9,9)], [(None,'none')],
      [(9,9),(1,2)], [(7,7),(7,7),(8,8),(7,77)],
      [(1,11),(1,111),(1,1111),(2,22),(2,222),('a','a'),('a','aa')],
      ])

    self.keyword_updates = [
      {}, {'1':1}, {'1':1,'2':2}, {'sup':'pumps','scewps':None}, {'aa':'aa'},
      ]

    # Items not initially in any of the multidict inputs self.inits.
    self.nonitems = [(44,44), (None,44), (55,None),('a','b'), (11,11), (22,22)]

    # Keys not initially in any of the multidict inputs self.inits or in
    # self.nonitems.
    self.nonkeys = [_unique, 'asdfasdosduf', 'oaisfiapsn', 'ioausopdaui']

    self.valuelist = [1, 2, 3, None, 'a', 'b', object()]

  def test_init(self):
    for init in self.inits:
      omd = omdict(init)
      assert omd.allitems() == init.items()

      omd1 = omdict(init)
      omd2 = omdict(omd1)
      assert omd1.allitems() == omd2.allitems()

  def test_load(self):
    omd = omdict()
    for init in self.inits:
      assert omd.load(init) == omd
      assert omd.allitems() == init.items()

  def test_copy(self):
    for init in self.inits:
      omd = omdict(init)
      copy = omd.copy()
      assert omd is not copy and omd == copy

  def test_clear(self):
    for init in self.inits:
      omd = omdict(init)
      omd.clear()
      assert omd.items() == []

  def test_fromkeys(self):
    for init in self.inits:
      keys = [key for key, value in init.items()]
      allitems = omdict.fromkeys(keys, _unique).allitems()
      assert allitems == zip(keys, repeat(_unique))

  def test_has_key(self):
    for init in self.inits:
      omd = omdict(init)
      for key, value in init.items():
        assert omd.has_key(key)

  def test_update(self):
    # Some manual tests.
    omd = omdict()
    omd.update([(1,1),(1,11),(2,2),(3,3),(1,111),(2,22)])
    assert omd.allitems() == [(1, 111), (2, 22), (3, 3)]

    omd = omdict([(1,1),(1,11),(2,2),(3,3),(1,111),(2,22)])
    omd.update({1:None,2:None,3:None})
    assert omd.allitems() == [(1,None),(2,None),(3,None)]
    
    for init in self.inits:
      for update, keyword_update in izip(self.updates, self.keyword_updates):
        omd1, omd2, omd3 = omdict(init), omdict(init), omdict(init)
        oldomd = omd1.copy()
        # Reduce the update to just the final items that will be present post
        # update(), where repeated keys will be reduced to their last occurring
        # value. For example, [(7,7),(7,8)] would be reduced to [(7,8)].
        reduced = [i for i in update.items() if i in odict(update).items()]

        # Update with a dictionary.
        omd1.update(update)
        # Update with keyword expansion.
        omd2.update(**keyword_update)
        # Update with both a dictionary and keyword expansion.
        omd3.update(update, **keyword_update)

        # Verification.
        if update or keyword_update:
          for key, value in reduced:
            assert key in omd1 and key in omd3
          for key, value in keyword_update.items():
            assert key in omd2 and key in omd3
        else:
          assert omd1 == omd2 == omd3 == oldomd

  def test_updateall(self):
    # Some manual tests.
    omd = omdict([(1,1),(1,11),(2,2),(3,3),(1,111),(2,22)])
    omd.updateall({1:None,2:None,3:None})
    assert omd.allitems() == [(1,None),(2,None),(3,None)]

    omd = omdict([(1,1),(1,11),(2,2),(3,3),(1,111),(2,22)])
    omd.updateall([(1,None),(2,None),(3,None),(1,None),(2,None)])
    assert omd.allitems() == [(1,None),(1,None),(2,None),(3,None),(2,None)]

    omd = omdict([(1,1),(1,11),(2,2),(3,3),(1,111),(2,22)])
    omd.updateall([(1,None),(1,None),(1,None),(2,None)])
    assert omd.allitems() == [(1,None),(1,None),(2,None),(3,3),(1,None)]

    for init in self.inits:
      for update, keyword_update in izip(self.updates, self.keyword_updates):
        omd1, omd2, omd3 = omdict(init), omdict(init), omdict(init)
        oldomd = omd1.copy()

        # Update with a dictionary.
        omd1.updateall(update)
        # Update with keyword expansion.
        omd2.updateall(**keyword_update)
        # Update with both a dictionary and keyword expansion.
        omd3.updateall(update, **keyword_update)

        # Verification.
        if update or keyword_update:
          for key, value in update.iteritems():
            assert key in omd1 and key in omd3
            assert value in omd1.getlist(key) and value in omd3.getlist(key)
          for key, value in keyword_update.items():
            assert key in omd2 and key in omd3
            assert omd2.getlist(key) == omd3.getlist(key) == [value]
        else:
          assert omd1 == omd2 == oldomd

  def test_get(self):
    for init in self.inits:
      omd = omdict(init)
      for key in omd.iterkeys():
        assert omd.get(key) == omd[key]
      for nonkey in self.nonkeys:
        assert omd.get(nonkey) is None
        assert omd.get(nonkey, _unique) == _unique

  def test_getlist(self):
    for init in self.inits:
      omd = omdict(init)
      for key in omd:
        assert omd.getlist(key) == [v for k,v in omd.allitems() if k == key]
      for nonkey in self.nonkeys:
        assert omd.getlist(nonkey) == []
        assert omd.getlist(nonkey, _unique) == _unique
      
  def test_setdefault(self):
    for init in self.inits:
      omd = omdict(init)
      for key in omd.iterkeys():
        assert omd.setdefault(key, _unique) == omd[key]
      for nonkey in self.nonkeys:
        assert omd.setdefault(nonkey) is None
        assert omd[nonkey] is None
      omd.load(init)
      for nonkey in self.nonkeys:
        assert omd.setdefault(nonkey, 123456) == 123456
        assert omd[nonkey] == 123456

  def test_setdefaultlist(self):
    for init in self.inits:
      omd = omdict(init)
      for key in omd.iterkeys():
        assert omd.setdefaultlist(key, _unique) == omd.getlist(key)
      for nonkey in self.nonkeys:
        assert omd.setdefaultlist(nonkey) == [None]
        assert omd.getlist(nonkey) == [None]
      omd.load(init)
      for nonkey in self.nonkeys:
        assert omd.setdefaultlist(nonkey, [1,2,3]) == [1,2,3]
        assert omd.getlist(nonkey) == [1,2,3]

    # setdefaultlist() with an empty list of values does nothing.
    for init in self.inits:
      omd = omdict(init)
      for key in omd.iterkeys():
        values = omd.getlist(key)
        assert key in omd
        assert omd.setdefaultlist(key, []) == values
        assert key in omd and omd.getlist(key) == values
      for nonkey in self.nonkeys:
        assert nonkey not in omd
        assert omd.setdefaultlist(nonkey, []) == []
        assert nonkey not in omd
        
  def test_add(self):
    for init in self.inits:
      omd = omdict(init)
      for key, value in self.nonitems:
        assert (key, value) not in omd.allitems()
        assert omd.add(key, value) == omd
        assert omd.getlist(key)[-1] == value
        assert omd.allitems()[-1] == (key, value)

      # Repeat the add() calls with the same items and make sure the old items
      # aren't replaced.
      oldomd = omd.copy()
      for key, value in self.nonitems:
        assert (key, value) in omd.allitems()
        assert omd.add(key, value) == omd
        assert len(omd.getlist(key)) == len(oldomd.getlist(key)) + 1
        assert omd.getlist(key)[-1] == value
        assert omd.allitems()[-1] == (key, value)

      # Assert that containers are valid values, too, not just immutables like
      # integers.
      assert omd.add(_unique, self.updates) == omd
      assert omd.getlist(_unique)[-1] == self.updates
      assert omd.allitems()[-1] == (_unique, self.updates)

      # Add() doesn't require a value, and when one isn't provided it defaults
      # to None.
      omd = omdict(init)
      assert omd.add(_unique) == omd
      assert _unique in omd and omd[_unique] == None

  def test_addlist(self):
    for init in self.inits:
      omd = omdict(init)
      for nonkey in self.nonkeys:
        assert (nonkey, self.valuelist) not in omd.allitems()
        assert omd.addlist(nonkey, self.valuelist) == omd
        assert omd.getlist(nonkey) == self.valuelist
        assert (omd.allitems()[-1 * len(self.valuelist):] ==
                zip(repeat(nonkey), self.valuelist))

      # Repeat the addlist() calls with the same items and make sure the old
      # items aren't replaced.
      oldomd = omd.copy()
      for nonkey in self.nonkeys:
        for value in self.valuelist:
          assert (nonkey, value) in omd.allitems()
        assert omd.addlist(nonkey, self.valuelist) == omd
        assert len(omd.getlist(nonkey)) == (len(oldomd.getlist(nonkey)) +
                                            len(self.valuelist))
        assert omd.getlist(nonkey) == oldomd.getlist(nonkey) + self.valuelist
        assert (omd.allitems()[-1 * len(self.valuelist):] ==
                zip(repeat(nonkey), self.valuelist))

      # If an empty list is provided to addlist(), nothing is added.
      omd = omdict(init)
      for nonkey in self.nonkeys:
        assert omd.addlist(nonkey) == omd and nonkey not in omd
        assert omd.addlist(nonkey, []) == omd and nonkey not in omd

  def test_setlist(self):
    for init in self.inits:
      omd = omdict(init)
      for key in (omd.keys() + self.nonkeys):
        if key in omd:
          assert omd.getlist(key) != self.valuelist
        assert omd.setlist(key, self.valuelist)
        assert key in omd and omd.getlist(key) == self.valuelist

    # Setting a key to an empty list is identical to deleting the key.
    for init in self.inits:
      omd = omdict(init)
      for nonkey in self.nonkeys:
        assert nonkey not in omd
        omd.setlist(nonkey, [])
        assert nonkey not in omd
      for key in omd.iterkeys():
        assert key in omd
        omd.setlist(key, [])
        assert key not in omd
      assert not omd

  def test_removevalues(self):
    for init in self.inits:
      omd = omdict(init)
      for nonkey in self.nonkeys:
        obj = object()
        values = [1, 1.1, '1.1', (), [], {}, obj, 5.5, '1.1']

        assert omd.removevalues(nonkey, []).getlist(nonkey) == []
        assert omd.removevalues(nonkey, values).getlist(nonkey) == []

        omd.addlist(nonkey, values).removevalues(nonkey, [])
        assert omd.getlist(nonkey) == values
        assert omd.removevalues(nonkey, values).getlist(nonkey) == []

        omd.addlist(nonkey, values)
        assert (omd.removevalues(nonkey, [1]).getlist(nonkey) == 
                [1.1, '1.1', (), [], {}, obj, 5.5, '1.1'])
        assert (omd.removevalues(nonkey, ['1.1', obj]).getlist(nonkey) ==
                [1.1, (), [], {}, 5.5])
        assert (omd.removevalues(nonkey, [[], 5.5, ()]).getlist(nonkey) ==
                [1.1, {}])
        assert omd.removevalues(nonkey, [{}]).getlist(nonkey) == [1.1]
        assert omd.removevalues(nonkey, [1.1]).getlist(nonkey) == []
        assert omd.removevalues(nonkey, [9, 9.9, 'nope']).getlist(nonkey) == []

  def test_pop(self):
    self._test_pop_poplist(lambda omd, key: omd.get(key) == omd.pop(key))
    
  def test_poplist(self):
    self._test_pop_poplist(lambda omd,key: omd.getlist(key) == omd.poplist(key))

  def _test_pop_poplist(self, assert_lambda):
    for init in self.inits:
      omd = omdict(init)
      items = omd.items()
      for key in list(omd.keys()):
        assert assert_lambda(omd, key)
        newitems = [item for item in items if item[0] != key]
        assert omd.items() == newitems
        items = newitems

      omd.load(init)
      for nonkey in self.nonkeys:
        self.assertRaises(KeyError, omd.pop, nonkey)
        assert omd.pop(nonkey, _unique) == _unique
        self.assertRaises(KeyError, omd.poplist, nonkey)
        assert omd.poplist(nonkey, _unique) == _unique

  def test_popvalue(self):
    # popvalue() with no value provided.
    for init in self.inits:
      for last in [True, False]:
        omd = omdict(init)
        allitems = omd.allitems()
        while omd.keys():
          for key in omd.keys():
            if last:
              value = omd.getlist(key)[-1]
              _rremove(allitems, (key, value))
            else:
              value = omd[key]
              allitems.remove((key, value))
              
            assert value == omd.popvalue(key, last=last)
            assert omd.allitems() == allitems

      omd.load(init)
      for nonkey in self.nonkeys:
        self.assertRaises(KeyError, omd.popvalue, nonkey)
        assert omd.popvalue(nonkey, default=_unique) == _unique

    # popvalue() with value provided.
    #   last = True (default).
    omd = omdict([(1,1), (2,2), (3,3), (2,2), (3,3), (2,2)])
    assert omd.popvalue(2, 2) == 2
    assert omd.allitems() == [(1,1), (2,2), (3,3), (2,2), (3,3)]
    assert omd.popvalue(2, 2) == 2
    assert omd.allitems() == [(1,1), (2,2), (3,3), (3,3)]
    assert omd.popvalue(2, 2) == 2
    assert omd.allitems() == [(1,1), (3,3), (3,3)]
    #   last = False.
    omd = omdict([(3,3), (2,2), (3,3), (2,2), (3,3), (2,2)])
    assert omd.popvalue(2, 2, last=True) == 2
    assert omd.allitems() == [(3,3), (2,2), (3,3), (2,2), (3,3)]
    assert omd.popvalue(2, 2, last=True) == 2
    assert omd.allitems() == [(3,3), (2,2), (3,3), (3,3)]
    assert omd.popvalue(2, 2, last=True) == 2
    assert omd.allitems() == [(3,3), (3,3), (3,3)]

    # Invalid key.
    self.assertRaises(KeyError, omd.popvalue, _unique, _unique)
    self.assertRaises(KeyError, omd.popvalue, _unique, 2)
    self.assertRaises(KeyError, omd.popvalue, _unique, 22)
    self.assertRaises(KeyError, omd.popvalue, _unique, _unique, last=False)
    self.assertRaises(KeyError, omd.popvalue, _unique, 2)
    self.assertRaises(KeyError, omd.popvalue, _unique, 22)
    assert omd.popvalue(_unique, _unique, 'sup') == 'sup'
    assert omd.popvalue(_unique, 2, 'sup') == 'sup'
    assert omd.popvalue(_unique, 22, 'sup') == 'sup'

    # Valid key, invalid value.
    self.assertRaises(ValueError, omd.popvalue, 3, _unique)
    self.assertRaises(ValueError, omd.popvalue, 3, _unique, False)

  def test_popitem(self):
    for init in self.inits:
      # All permutations of booleans <fromall> and <last>.
      for fromall, last in product([True,False], repeat=2):
        omd = omdict(init)
        allitems = omd.allitems()
        while omd.allitems():
          if fromall:
            key, value = omd.allitems()[-1 if last else 0]
          else:
            key = omd.keys()[-1 if last else 0]
            value = omd[key]

          popkey, popvalue = omd.popitem(fromall=fromall, last=last)
          assert popkey == key and popvalue == value

          if fromall:
            if last:
              _rremove(allitems, (key, value))
            else:
              allitems.remove((key, value))
          else:
            allitems = [(k,v) for k,v in allitems if k != key]
          assert omd.allitems() == allitems

      omd = omdict()
      self.assertRaises(KeyError, omd.popitem)

  def test_poplistitem(self):
    for init in self.inits:
      for last in [True,False]:
        omd, omdcopy = omdict(init), omdict(init)
        while omd.keys():
          key, valuelist = omd.poplistitem(last=last)
          assert key == omdcopy.keys()[-1 if last else 0]
          assert valuelist == omdcopy.getlist(key)
          omdcopy.pop(omdcopy.keys()[-1 if last else 0])
          
        # poplistitem() on an empty omdict.
        self.assertRaises(KeyError, omd.poplistitem)

  # Tests every non-'all' items, keys, values, lists method: items(), keys(),
  # values(), lists(), listitems() and their iterators iteritems(), iterkeys(),
  # itervalues(), iterlists(), and iterlistitems().
  def test_nonall_item_key_value_lists(self):
    for init in self.inits:
      dic = odict(init.items())
      omd = omdict(init.items())

      # Testing items(), keys(), values(), lists(), and listitems().
      assert omd.items() == dic.items()
      assert omd.keys() == dic.keys()
      assert omd.values() == dic.values()
      iterator = izip(omd.keys(), omd.lists(), omd.listitems())
      for key, valuelist, listitem in iterator:
        assert omd.values(key) == omd.getlist(key) == valuelist
        assert omd.items(key) == [i for i in init.items() if i[0] == key]
        assert listitem == (key, valuelist)

      # Testing iteritems(), iterkeys(), itervalues(), and iterlists().
      for key1, key2 in izip(omd.iterkeys(), dic.iterkeys()):
        assert key1 == key2
      for val1, val2 in izip(omd.itervalues(), dic.itervalues()):
        assert val1 == val2
      for item1, item2 in izip(omd.iteritems(), dic.iteritems()):
        assert item1 == item2
      for key, values in izip(omd.iterkeys(), omd.iterlists()):
        assert omd.getlist(key) == values
      iterator = izip(omd.iterkeys(), omd.iterlists(), omd.iterlistitems())
      for key, valuelist, listitem in iterator:
        assert listitem == (key, valuelist)
        
      # Test iteritems() and itervalues() with a key.
      for key in omd.iterkeys():
        assert list(omd.iteritems(key)) == zip(repeat(key), omd.getlist(key))
        assert list(omd.iterallitems(key)) == zip(repeat(key), omd.getlist(key))
      for nonkey in self.nonkeys:
        self.assertRaises(KeyError, omd.iteritems, nonkey)
        self.assertRaises(KeyError, omd.itervalues, nonkey)

  # Tests every 'all' items, keys, values method: allitems(), allkeys(),
  # allvalues() and their iterators iterallitems(), iterallkeys(),
  # iterallvalues().
  def test_all_items_keys_values_iterall_items_keys_values(self):
    for init in self.inits:
      omd = omdict(init)
      # map(list, zip(*lst)) - doesn't work if lst is empty, lst == [].
      keys = [key for key, value in init.items()]
      values = [value for key, value in init.items()]

      # Test allitems(), allkeys(), allvalues().
      assert omd.allitems() == init.items()
      assert omd.allkeys() == keys
      assert omd.allvalues() == values

      # Test iterallitems(), iterallkeys(), iterallvalues().
      for key1, key2 in zip(omd.iterallkeys(), keys):
        assert key1 == key2
      for val1, val2 in zip(omd.iterallvalues(), values):
        assert val1 == val2
      for item1, item2 in zip(omd.iterallitems(), init.items()):
        assert item1 == item2

      # Test allitems(), allvalues(), iterallitems() and iterallvalues() with a
      # key.
      for key in omd.iterkeys():
        assert (omd.allvalues(key) == list(omd.iterallvalues(key)) ==
                omd.getlist(key))
        assert (omd.allitems(key) == list(omd.iterallitems(key)) ==
                zip(repeat(key), omd.getlist(key)))
      for nonkey in self.nonkeys:
        self.assertRaises(KeyError, omd.allvalues, nonkey)
        self.assertRaises(KeyError, omd.allitems, nonkey)
        self.assertRaises(KeyError, omd.iterallvalues, nonkey)
        self.assertRaises(KeyError, omd.iterallitems, nonkey)

  def test_reverse(self):
    for init in self.inits:
      assert omdict(init).reverse().allitems() == init.items()[::-1]

  def test_eq(self):
    for init in self.inits:
      d, omd = dict(init), omdict(init)
      assert d == omd and omd == omd and omd == omd.copy()

  def test_ne(self):
    diff = omdict([(_unique, _unique)])
    for init in self.inits:
      assert omdict(init) != diff
      # Compare to basic types.
      for basic in [1, 1.1, '1.1', (), [], object()]:
        assert omdict(init) != basic

  def test_len(self):
    for init in self.inits:
      assert len(omdict(init)) == len(dict(init))

  def test_size(self):
    for init in self.inits:
      assert omdict(init).size() == len(init)

  def test_iter(self):
    for init in self.inits:
      omd = omdict(init)
      for key1, key2 in izip_longest(iter(omd), omd.iterkeys()):
        assert key1 == key2

  def test_contains(self):
    for init in self.inits:
      omd = omdict(init)
      for key, value in init.items():
        assert key in omd

  def test_getitem(self):
    for init in self.inits:
      dic = dict(init)
      omd = omdict(init)
      for key in omd.iterkeys():
        assert omd[key] == dic[key]

    omd = omdict()
    self.assertRaises(KeyError, omd.__getitem__, _unique)

  def test_set_setitem(self):
    for init in self.inits:
      omd = omdict()
      omd2 = omdict()
      for key, value in init.items():
        omd[key] = value
        assert omd2.set(key, value) == omd2
        assert omd == omd2 and omd[key] == value

      # Store containers as values, not just immutables like integers.
      omd[_unique] = self.valuelist
      assert omd2.set(_unique, self.valuelist) == omd2
      assert omd == omd2 and omd[_unique] == self.valuelist

  def test_delitem(self):
    for init in self.inits:
      omd = omdict(init)
      for key in list(omd.keys()):
        assert key in omd
        del omd[key]
        assert key not in omd

  def test_nonzero(self):
    for init in self.inits:
      if init:
        assert omdict(init)
      else:
        assert not omdict(init)

  def test_str(self):
    for init in self.inits:
      omd = omdict(init)
      s = '{%s}'%', '.join(map(lambda p: '%s: %s'%(p[0], p[1]), omd.allitems()))
      assert s == str(omd)

  def test_odict_omdict_parity(self):
    for init in self.inits:
      d = odict(init)
      omd = omdict(init)

      self._compare_odict_and_omddict(d, omd)
      self._compare_odict_and_omddict(d.copy(), omd.copy()) # copy().
      d.clear(), omd.clear() # clear().
      self._compare_odict_and_omddict(d, omd) 

      assert dict().update(init) == omdict().update(init) # update().
      assert d.fromkeys(init).items() == omd.fromkeys(init).items() # fromkeys()

  def _compare_odict_and_omddict(self, d, omd):
    assert len(d) == len(omd) # __len__().

    # __contains__(), has_key(), get(), and setdefault().
    for dkey, omdkey in izip(d, omd):
      assert dkey == omdkey and dkey in d and omdkey in omd
      assert d.has_key(dkey) and omd.has_key(omdkey)
      assert d.get(dkey) == omd.get(omdkey)
      d.setdefault(dkey, _unique)
      omd.setdefault(omdkey, _unique)
      assert d.get(dkey) == omd.get(omdkey) and d.get(dkey) != _unique
    for nonkey in self.nonkeys:
      assert d.get(nonkey) == omd.get(nonkey) == None
      d.setdefault(nonkey, _unique)
      omd.setdefault(nonkey, _unique)
      assert d.get(nonkey) == omd.get(nonkey) == _unique

    # items(), keys, values(), iteritems(), iterkeys, and itervalues().
    iterators = [
      izip(d.items(), omd.items(), d.keys(), omd.keys(),
           d.values(), omd.values()),
      izip(d.iteritems(), omd.iteritems(), d.iterkeys(), omd.iterkeys(),
           d.itervalues(), omd.itervalues())]
    for iterator in iterators:
      for ditem, omditem, dkey, omdkey, dvalue, omdvalue in iterator:
        assert ditem == omditem and dkey == omdkey and dvalue == omdvalue

    # pop().
    dcopy, omdcopy = d.copy(), omd.copy()
    while dcopy and omdcopy:
      assert dcopy.pop(dcopy.keys()[0]) == omdcopy.pop(omdcopy.keys()[0])
    # popitem().
    dcopy, omdcopy = d.copy(), omd.copy()
    while dcopy and omdcopy:
      assert dcopy.popitem() == omdcopy.popitem()

    # __getitem__().
    for dkey, omdkey in izip(d.iterkeys(), omd.iterkeys()):
      assert d[dkey] == omd[omdkey]
    # __setitem__().
    for dkey, omdkey in izip(d, omd):
      d[dkey] = _unique
      omd[omdkey] = _unique
      assert dkey == omdkey and d[dkey] == omd[omdkey]
    # __delitem__().
    while d and omd:
      dkey, omdkey = d.keys()[0], omd.keys()[0]
      del d[dkey]
      del omd[omdkey]
      assert dkey == omdkey and dkey not in d and omdkey not in omd

  def test_fundamentals(self):
    # Gets, sets, and pops.
    omd = omdict()
    omd[1] = 1
    omd[2] = 2
    assert omd.allitems() == [(1,1),(2,2)]
    omd[1] = 11
    assert omd.allitems() == [(1,11),(2,2)]
    omd.add(1, 1.1)
    assert omd.allitems() == [(1,11),(2,2),(1,1.1)]
    assert omd.popvalue(1) == 1.1
    assert omd.allitems() == [(1,11),(2,2)]
    omd.popvalue(2)
    assert omd.allitems() == [(1,11)]
    omd[2] = [2,2]
    assert omd.allitems() == [(1,11),(2,[2,2])]
    omd[1] = None
    assert omd.allitems() == [(1,None),(2,[2,2])]
    omd.add(2, None)
    assert omd.allitems() == [(1,None),(2,[2,2]),(2,None)]
    del omd[2]
    assert omd.allitems() == [(1,None)]
    omd[3] = 3
    assert omd.allitems() == [(1,None),(3,3)]
    omd.setlist(1, [1,11,111])
    assert omd.allitems() == [(1,1),(3,3),(1,11),(1,111)]
    omd.addlist(1,[1111])
    omd = omdict([(1,1),(3,3),(1,11),(1,111),(1,1111)])
    assert omd.allitems() == [(1,1),(3,3),(1,11),(1,111),(1,1111)]
    omd[1] = None
    assert omd.allitems() == [(1,None),(3,3)]

  def test_pops(self):
    init = [(1,1),(2,2),(1,1),(1,2),(1,3)]

    # pop().
    omd = omdict(init)
    assert omd.pop(1) == 1
    assert omd.allitems() == [(2,2)]
    assert omd.pop(_unique, 'sup') == 'sup'

    # poplist().
    omd = omdict(init)
    assert omd.poplist(1) == [1,1,2,3]
    assert omd.allitems() == [(2,2)]
    self.assertRaises(KeyError, omd.poplist, _unique)
    assert omd.poplist(_unique, 'sup') == 'sup'

    # popvalue().
    omd = omdict(init)
    assert omd.popvalue(1) == 3
    assert omd.allitems() == [(1,1),(2,2),(1,1),(1,2)]
    self.assertRaises(KeyError, omd.popvalue, _unique)
    assert omd.popvalue(_unique, default='sup') == 'sup'
    assert omd.popvalue(1, last=False) == 1
    assert omd.allitems() == [(2,2),(1,1),(1,2)]

    # popitem().
    omd = omdict(init)
    assert omd.popitem() == (2,2)
    assert omd.allitems() == [(1,1),(1,1),(1,2),(1,3)]
    assert omd.popitem() == (1,1)
    assert omd.allitems() == []
    omd = omdict(init)
    assert omd.popitem(fromall=True) == (1,3)
    assert omd.allitems() == [(1,1),(2,2),(1,1),(1,2)]
    assert omd.popitem(fromall=True, last=False) == (1,1)
    assert omd.allitems() == [(2,2),(1,1),(1,2)]


class TestUtilities(unittest.TestCase):
  def test_rfind(self):
    tests = [([], 1, -1), ([1], 1, 0), ([1,2], 2, 1), ([1,2,1,2], 1, 2),
             ([1,2,3], 4, -1), ([1,2,3], 1, 0)]
    for lst, item, pos in tests:
      assert _rfind(lst, item) == pos

  def test_rremove(self):
    tests = [([1,1], 1, [1]), ([1], 1, []), ([1,2], 2, [1]),
             ([1,2,3], 1, [2,3]), ([1,2,1,2], 1, [1,2,2]),
             ([1,2,1], 1, [1,2])]
    for lst, item, result in tests:
      _rremove(lst, item)
      assert lst == result

    nonitems = [None, 'asdf', object(), 1000000]
    for nonitem in nonitems:
      self.assertRaises(ValueError, _rremove, lst, nonitem)      


def _rfind(lst, item):
  """
  Returns the index of the last occurance of <item> in <lst>. Returns -1 if
  <item> is not in <l>.
    ex: _rfind([1,2,1,2], 1) == 2
  """
  try:
    return (len(lst) - 1) - lst[::-1].index(item)
  except ValueError:
    return -1

def _rremove(lst, item):
  """
  Removes the last occurance of <item> in <lst>, or raises a ValueError if
  <item> is not in <list>.
    ex: _rremove([1,2,1,2], 1) == [1,2,2]
  """
  pos = _rfind(lst, item)
  if pos >= 0:
    lst.pop(pos)
    return lst
  raise ValueError('_rremove(list, x): x not in list')
