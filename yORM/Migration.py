class Migration(dict):
    def __init__(self, **kwargs):
        for k,v in self.migrate_from(**kwargs).iteritems():
            self[k] = v
    
    def process(self):
        new = self.migrate()
        for name, v in self.iteritems():
            if str(name)[0:3] == str('_b_'):
                new[name] = v
        return new

def migrate
     new = self
     new[title] = self.title.lowercase()
     new[body] = self.content
     del new['content']
     return new