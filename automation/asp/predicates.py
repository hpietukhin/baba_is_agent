"""Clorm predicate classes mapping ASP atoms to Python objects."""

from clorm import ConstantField, IntegerField, Predicate


class AtInit(Predicate):
    """Position of an object on the grid at time T=0."""

    obj_id = IntegerField()
    obj_type = ConstantField()
    x = IntegerField()
    y = IntegerField()


class RuleIs(Predicate):
    """A parsed rule: subject IS target."""

    subject = ConstantField()
    target = ConstantField()


class TextBlock(Predicate):
    """Position of a text block (used for dynamic rule activation)."""

    block_id = IntegerField()
    block_type = ConstantField()
    x = IntegerField()
    y = IntegerField()


class Do(Predicate):
    """Selected action at a given time step. Maps to ASP atom 'do'."""

    direction = ConstantField()
    time = IntegerField()
