"""Recursive descent parser: token sequences → AST RuleNodes."""

from __future__ import annotations

from automation.asp.ast_nodes import (
    OperatorNode,
    RuleNode,
    SubjectNode,
    TargetNode,
)
from automation.asp.lexer import TokenCategory, classify_token


def parse_rules(
    sequences: list[list[tuple[int, int, str]]],
) -> list[RuleNode]:
    """Parse horizontal/vertical token sequences into RuleNode ASTs.

    Supported grammar (MVP): SUBJECT IS TARGET
    where SUBJECT is a noun, IS is the operator, TARGET is a property or noun.
    """
    rules: list[RuleNode] = []

    for seq in sequences:
        tokens = [(x, y, t) for x, y, t in seq]
        i = 0
        while i < len(tokens) - 2:
            _x1, _y1, tok_subj = tokens[i]
            _x2, _y2, tok_op = tokens[i + 1]
            _x3, _y3, tok_target = tokens[i + 2]

            cat_subj = classify_token(tok_subj)
            cat_op = classify_token(tok_op)
            cat_target = classify_token(tok_target)

            if (
                cat_subj == TokenCategory.NOUN
                and cat_op == TokenCategory.OPERATOR
                and cat_target in (TokenCategory.PROPERTY, TokenCategory.NOUN)
            ):
                rules.append(
                    RuleNode(
                        subject=SubjectNode(noun=tok_subj),
                        operator=OperatorNode(op=tok_op),
                        target=TargetNode(
                            value=tok_target,
                            is_property=(cat_target == TokenCategory.PROPERTY),
                        ),
                    )
                )
                i += 3
            else:
                i += 1

    return rules
