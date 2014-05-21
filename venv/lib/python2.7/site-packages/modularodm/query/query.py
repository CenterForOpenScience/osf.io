
class QueryBase(object):

    def __or__(self, other):
        return QueryGroup('or', self, other)

    def __and__(self, other):
        return QueryGroup('and', self, other)

    def __invert__(self):
        return QueryGroup('not', self)

class QueryGroup(QueryBase):

    def __init__(self, operator, *args):

        self.operator = operator

        self.nodes = []
        for node in args:
            if not isinstance(node, QueryBase):
                raise TypeError('Nodes must be Query objects.')
            if isinstance(node, QueryGroup) and node.operator == operator:
                self.nodes += node.nodes
            else:
                self.nodes.append(node)

    def __repr__(self):

        return '{0}({1})'.format(
            self.operator.upper(),
            ', '.join(repr(node) for node in self.nodes)
        )

class RawQuery(QueryBase):

    def __init__(self, attribute, operator, argument):

        self.attribute = attribute
        self.operator = operator
        self.argument = argument

    def __repr__(self):

        return 'RawQuery({}, {}, {})'.format(
            self.attribute,
            self.operator,
            self.argument
        )
