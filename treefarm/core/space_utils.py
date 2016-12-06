from collections.abc import Sequence, Mapping, Set
from itertools import chain


from .domains import Interval
from .spaces import (
    Apply, Combination, Primitive, Parameter, prod, join,
    Categorical, Discrete, Continuous)


def expand(search_space, index_vector, include_primitives=False):
    # TODO shall accept slices?
    # TODO how to index numerical primitives?
    # TODO no index with strings yet

    fcs = fc_shape(search_space, include_primitives)
    assert len(index_vector) == len(fcs)

    index_iter = iter(index_vector)

    def _expand(search_space):
        if type(search_space) == Apply:
            dom = search_space.domain
            op = search_space.operation
            if isinstance(op, Combination):
                if op == join:
                    # TODO get a problem here, if indexed by key!!
                    return dom[next(index_iter)]
                else:
                    raise NotImplementedError(
                        'Join only as combination allowed.')
            else:
                if isinstance(op, Apply):
                    op = _expand(op)

                chosen_values = map(_expand, dom.values())
                params = zip(dom.keys(), chosen_values)
                dom = ParameterList.from_items(params)
                return Apply(op, dom)

        elif isinstance(search_space, Primitive):
            if include_primitives:
                val = next(index_iter)
                if val in search_space.domain:
                    return val
                else:
                    raise KeyError('%s not in primitive.')
            else:
                return search_space
        else:
            raise NotImplementedError('Not a parameter.')

    return _expand(search_space)


def fc_shape(search_space, include_primitives=True):
    """
    Returns the flat choice shape of a search space.

    """
    _fc_shape = lambda ss : fc_shape(ss, include_primitives)

    shape = []
    if type(search_space) == Apply:
        dom = search_space.domain
        op = search_space.operation
        if isinstance(op, Combination):
            if op == join:
                shape.append(len(dom))
            else:
                raise NotImplementedError('Only join as combination allowed.')
        else:
            if isinstance(op, Apply):
                subshapes = _fc_shape(op)
                shape.extend(subshapes)

            subshapes = map(_fc_shape, dom)
            shape.extend(chain(*subshapes))

    elif isinstance(search_space, Primitive):
        if include_primitives:
            shape.append(len(search_space))

    else:
        raise NotImplementedError('Not a parameter.')

    return tuple(shape)


def get_crown(search_space, include_primitives=True):
    crown = []
    indices = []

    def _find_choice_points(subspace, index):
        is_cp = False
        if isinstance(subspace, Apply):
            if subspace.operation == join:
                is_cp = True
            else:
                _find_choice_points(subspace.operation, (*index, -1))
                for i, subs in enumerate(subspace.domain):
                    _find_choice_points(subs, (*index, i))
        elif isinstance(subspace, Primitive) and include_primitives:
            is_cp = True

        if is_cp:
            crown.append(subspace)
            indices.append(index)

    _find_choice_points(search_space, ())
    return crown, indices


def get_subspace(subspace, index):
    for i in index:
        if i == -1:
            subspace = subspace.operator
        else:
            subspace = subspace.domain[i]
    return subspace


def to_space(arg):
    """Convert nested structures to treefarm spaces."""

    print('arg1', arg)
    arg = spacify(arg)
    print('arg2', arg)
    if type(arg) == dict:
        return prod(**arg)
    if type(arg) == set:
        if converts_to_primitive(arg):
            return Categorical(arg)
        else:
            return join(*arg)
    if type(arg) == Interval:
        if arg.step == 0:
            return Continuous(arg)
        else:
            return Discrete(arg)
    else:
        return arg


def spacify(arg):
    """Converts elements of a Sequence or Mappings to spaces."""

    if isinstance(arg, dict):
        return {k:to_space(v) for k,v in arg.items()}
    elif isinstance(arg, (list, set)):
        return type(arg)(to_space(val) for val in arg)
    else:
        return arg


def converts_to_primitive(arg):
    """Test if the elements of a Sequence are Values."""
    for element in arg:
        if isinstance(element, (Parameter, Interval, dict, list, set)):
            return False
    return True
