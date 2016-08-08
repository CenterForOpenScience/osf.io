from api.base.parsers import JSONAPIParser, JSONAPIParserForRegularJSON


class PreprintsJSONAPIParser(JSONAPIParser):
    def flatten_relationships(self, relationships):
        ret = super(PreprintsJSONAPIParser, self).flatten_relationships(relationships)
        if ret.get('target_type') and ret.get('id'):
            return {ret['target_type']: ret['id']}
        return ret


class PreprintsJSONAPIParserForRegularJSON(JSONAPIParserForRegularJSON):
    def flatten_relationships(self, relationships):
        ret = super(PreprintsJSONAPIParserForRegularJSON, self).flatten_relationships(relationships)
        if ret.get('target_type') and ret.get('id'):
            return {ret['target_type']: ret['id']}
        return ret
