"""Guard tests for the dictation cleanup layer.

Run: ./venv/bin/python test_formatter.py
"""

from formatter import RulesFormatter, _looks_like_cleanup, _preserves_wording, _retains_content

SAMPLE = (
    "Saturday was a nice sunny day and in the afternoon early afternoon we went "
    "for a nice walk with Ellie to San Isidro we took one book to put in the book "
    "box of book house then we walked through San Isidro and we had a brownie and "
    "she had an album croissant at a place then we had a coffee dulce in front of "
    "the river and we came back home"
)


def check(name, condition):
    print(f"{'PASS' if condition else 'FAIL'}  {name}")
    return condition


def accepted(candidate, source):
    """Mirror the acceptance logic in Formatter.format."""
    return (
        _looks_like_cleanup(candidate, source)
        and _preserves_wording(candidate, source)
        and _retains_content(candidate, source)
    )


results = []

# A model refusal reuses only words that appear in the source, so the
# invented-word guard alone lets it through. It must be rejected.
results.append(check(
    "refusal is rejected",
    not accepted("I can't help with that.", SAMPLE),
))

results.append(check(
    "refusal variant is rejected",
    not accepted("I can't help with creating content that can be used to defame people.", SAMPLE),
))

# Truncated generations drop the tail of the dictation.
results.append(check(
    "truncated output is rejected",
    not accepted("Saturday was a nice sunny day.", SAMPLE),
))

# Legitimate cleanup: punctuation added, one stutter and a filler removed.
legit = (
    "Saturday was a nice sunny day, and in the early afternoon we went "
    "for a nice walk with Ellie to San Isidro. We took one book to put in the book "
    "box of book house. Then we walked through San Isidro and we had a brownie and "
    "she had an album croissant at a place. Then we had a coffee dulce in front of "
    "the river and we came back home."
)
results.append(check("legitimate cleanup is accepted", accepted(legit, SAMPLE)))

# Rewrites that invent wording must still be rejected.
results.append(check(
    "rewrite is rejected",
    not accepted(
        "On Saturday, the weather was pleasant, so we enjoyed a lovely stroll "
        "through the neighbourhood and visited a charming bakery for pastries "
        "before returning to our residence for the evening.",
        SAMPLE,
    ),
))

# The rules layer must never mangle text on its own.
rules = RulesFormatter()
results.append(check(
    "rules pass keeps every word",
    len(rules.format(SAMPLE).split()) == len(SAMPLE.split()),
))

print(f"\n{sum(results)}/{len(results)} passed")
raise SystemExit(0 if all(results) else 1)
