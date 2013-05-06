###############################################################################

import types

import re

import bson # RUINING ABSTACTION

import logging; 
logging.basicConfig(level=logging.DEBUG); 
logger = logging.getLogger('Object')

class Object(dict):
    ###########################################################################
    # Class Mapper
    ###########################################################################
    
    __classes__ = {}
    
    @classmethod
    def register(cls, **kwargs):
        cls.__classes__[cls.__name__.lower()] = cls
    
    ###########################################################################
    # Sessions
    ###########################################################################
    # TODO What happens when it's loaded, but dirty?
    
    __session__ = {}
    
    def getClassName(self):
        return self.__class__.__name__.lower()
    
    def addToSession(self):
        clsName = self.getClassName()
        if clsName not in self.__session__:
            self.__session__[clsName] = {}
        if self._id not in self.__session__[clsName]:
            self.__session__[clsName][self._id] = self
    
    @classmethod
    def retrieveFromSession(self, key):
        try:
            return self.__session__[self.__name__.lower()][key]
        except KeyError:
            return None
    
    ###########################################################################
    # Migration
    ###########################################################################
    
    #@classmethod
    #def _migrate(self, data):
    #    # TODO What if a backref name is changed; it should go to those objects and rename field
    #    migrated = False
    #    if data and '_doc' in data and 'version' in data['_doc']:
    #        if str(data['_doc']['version']) is not str(self._doc['version']):
    #            obj = self.Migrate(**data)
    #            data = obj.process()
    #            migrated = True
    #    return (migrated, data)
    
    ###########################################################################    
    # Foreign Relationships
    ###########################################################################
    
    @property
    def ref(self):
        return self.storage.getRef(self)
    
    def makeBackRefName(self, name):
        return '_b_' + self.getClassName() + '_' + name
    
    def isBackRef(self, name):
        name = str(name)
        if name[0:3] == '_b_':
            return name.split('_')[2:4]
        else:
            return False
    
    def setBackRef(self, field, obj):
        if isinstance(field, list):
            field = field[0]
            fieldName = self.makeBackRefName(field)
            if fieldName not in obj:
                obj[fieldName] = self.ObjectList(obj, fieldName, self.__class__)
            if self.ref not in obj[fieldName]:
                obj[fieldName].append(self)
        else:
            fieldName = self.makeBackRefName(field)
            obj[fieldName] = self.ref
        obj.save()
        return True
    
    ###########################################################################
    ###########################################################################
    
    def getSchemaType(self, name):
        if name in self.schema and 'type' in self.schema[name]:
            schemaNameType = self.schema[name]['type']
            if isinstance(schemaNameType, list):
                if len(schemaNameType) > 0:
                    return schemaNameType[0]
            else:
                return schemaNameType
        return None
            
    def isSchemaTypeAList(self, name):
        try:
            if isinstance(self.schema[name]['type'], list):
                return True 
        except KeyError:pass
        return False
        
    @classmethod
    def setStorage(cls, storage):
        cls.storage = storage
        cls.register()
    
    @classmethod
    def load(cls, key):
        #fromSession = cls.retrieveFromSession(key)
        #if fromSession:
        #    return fromSession
        #else:
        #if not key:
        #    return cls.ObjectNone()
        if 'type' in cls.schema['_id'] and cls.schema['_id']['type']  == bson.ObjectId:
            key = bson.ObjectId(str(key))
        data = cls.storage.get(key)
        if not data:
            return cls.ObjectNone()
        #migrated, data = cls._migrate(data)
        newObj = cls(**data)
        #if migrated:
        #    newObj.save()
        newObj.addToSession()
        return newObj
    
    def remove(self, are_you_sure=False, backrefs=True):
        for k,v in self.schema.iteritems():
            if 'backref' in v:
                field = v['backref']
                is_backref_a_list = False
                if isinstance(field, list):
                    field = field[0]
                    is_backref_a_list = True
                
                field_name = self.makeBackRefName(field)

                if self.isSchemaTypeAList(k):
                    if len(self[k]) > 0:
                        if is_backref_a_list:
                            for obj in self.__getattr__(k).objects():
                                try:
                                    obj[field_name].remove(self.ref)
                                    obj.save()
                                except:pass
                        else:
                            for obj in self.__getattr__(k).objects():
                                try:
                                    obj[field_name] = None
                                    obj.save()
                                except:pass
                else:
                    if self[k]:
                        obj = self.__getattr__(k)
                        try:
                            if is_backref_a_list:
                                obj[field_name].remove(self.ref)
                            else:
                                obj[field_name] = None
                            obj.save()
                        except:pass

        self.storage.db.remove({'_id':self.ref})

    def insert(self):
        return self.storage.set('id', self)
    
    def save(self):
        for i in self.dirty:
            i[0](i[1], i[2])
        self.storage.update('id', self)
        self.dirty = []
        self.addToSession()
        return True
    
    @classmethod
    def find(self, **kwargs):
        return self.storage.find(**kwargs)
    
    ###########################################################################
    # Overloading
    ###########################################################################
    
    def __init__(self, **kwargs):
        self.dirty = []
        
        #######################################################################
        # Set the document info
        #######################################################################
        self['_doc'] = self._doc
        
        #######################################################################
        # Set defaults
        #######################################################################
        for k,v in self.schema.iteritems():
            if 'default' in v:
                default_value = v['default']
                if isinstance(default_value, types.LambdaType):
                    self[k]=default_value()
                elif isinstance(default_value, types.FunctionType):
                    self[k]=default_value()
                else:
                    self[k]=default_value
            else:
                if self.isSchemaTypeAList(k):
                    self[k] = self.ObjectList(self, k, self.getSchemaType(k))
                else:
                    super(Object, self).__setitem__(k, None)
        
        #######################################################################
        # Migrate if needed
        #######################################################################
        #migrated, kwargs = self._migrate(kwargs)

        #######################################################################
        # Set the document info
        #######################################################################
        for k,v in kwargs.iteritems():
            if isinstance(v, list):
                # TODO What if len(v) is 0; if schema set class, elif  len(v) is 0 delete backref
                if self.isSchemaTypeAList(k):
                    v = self.ObjectList(self, k, self.getSchemaType(k), v)
                elif len(v) > 0 and self.isBackRef(k):
                    typ = self.isBackRef(k)[0]
                    v = self.ObjectList(self, k, self.__classes__[typ], v)
                #elif len(v) > 0:
                #    if v[0].collection:
                #        v = self.ObjectList(self, k, self.__classes__[v[0].collection], v)
                super(Object, self).__setitem__(k, v)            
            else:
                super(Object, self).__setitem__(k, v)
    
    ###########################################################################
    # Overloading
    ###########################################################################
    
    def __getitem__(self, name):
        return super(Object, self).__getitem__(name)
    
    def __setitem__(self, name, value):
        if name in self.schema or name is '_doc' or str(name)[0:3] == str('_b_'):
            if not self.isSchemaTypeAList(name):
                schemaType = self.getSchemaType(name)
                if schemaType and isinstance(schemaType(), Object) and value:
                    if 'backref' in self.schema[name]:
                        self.dirty.append((lambda name, obj: self.setBackRef(name, obj), self.schema[name]['backref'], value))
                    value = value.ref
            super(Object, self).__setitem__(name, value)
        else:
            super(Object, self).__setattr__(name, value)
    
    def __getattr__(self, name):
        try:
            value = self[name]
            schemaType = self.getSchemaType(name)
            if schemaType and isinstance(schemaType(), Object) and value and not self.isSchemaTypeAList(name):
                return schemaType.load(value)
            else:
                return value
        except KeyError:
            if '_b_'+name in self:
                value = self.__getitem__('_b_'+name)
                if not isinstance(value, list):
                    return self.__classes__[re.match('_b_(.*?)_.*', '_b_node_parent').group(1)].load(value)
                return self.__getitem__('_b_'+name)
            else:
                return None
    
    def __setattr__(self, name, value):
        self.__setitem__(name, value)
    
    ###########################################################################
    # Object Objects
    ###########################################################################
    
    class ObjectNone(dict):
        def __setattr__(self, name, value):
            return None
        def __setitem__(self, name, value):
            return None
        def __getattr__(self, name):
            return None
        def __getitem__(self, name):
            return None
    
    class ObjectList(list):
        
        def __init__(self, parent, schemaName, typ, *args):
            self.name = schemaName
            self.parent = parent
            self.type = typ
            super(self.__class__, self).__init__(*args)
        
        def objects(self):
            if self.type and isinstance(self.type(), Object):
                return [self.type.load(x) for x in self]
            return self
        
        def object(self, index):
            if self.type and isinstance(self.type(), Object):
                return self.type.load(self[index])
            return self
        
        # def __setitem__(self, index, value)
        
        def append(self, value):
            if self.type and isinstance(self.type(), Object) and value:
                if self.name in self.parent.schema and 'backref' in self.parent.schema[self.name]:
                    self.parent.dirty.append((lambda name, obj: self.parent.setBackRef(name, obj), self.parent.schema[self.name]['backref'], value))
                value = value.ref
            super(self.__class__, self).append(value)
    
    class ObjectDict(dict):
        pass
