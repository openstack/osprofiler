# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
Guidelines for writing new hacking checks

 - Use only for OSProfiler specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range N3xx. Find the current test with
   the highest allocated number and then pick the next value.
 - Keep the test method code in the source file ordered based
   on the N3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to tests/unit/test_hacking.py

"""

import functools
import re
import tokenize
from collections.abc import Callable, Generator
from typing import Any

from hacking import core  # type: ignore[import-not-found]

re_no_construct_dict = re.compile(r"\sdict\(\)")
re_no_construct_list = re.compile(r"\slist\(\)")
re_str_format = re.compile(
    r"""
%            # start of specifier
\(([^)]+)\)  # mapping key, in group 1
[#0 +\-]?    # optional conversion flag
(?:-?\d*)?   # optional minimum field width
(?:\.\d*)?   # optional precision
[hLl]?       # optional length modifier
[A-z%]       # conversion modifier
""",
    re.X,
)
re_raises = re.compile(r"\s:raise[^s] *.*$|\s:raises *:.*$|\s:raises *[^:]+$")


@core.flake8ext  # type: ignore[untyped-decorator]
def skip_ignored_lines(
    func: Callable[..., Any],
) -> Callable[..., Any]:

    @functools.wraps(func)
    def wrapper(
        logical_line: str, filename: str
    ) -> Generator[tuple[int, str], None, None]:
        line = logical_line.strip()
        if not line or line.startswith("#") or line.endswith("# noqa"):
            return
        try:
            yield next(func(logical_line, filename))
        except StopIteration:
            return

    return wrapper


def _parse_assert_mock_str(
    line: str,
) -> tuple[int, str, str] | tuple[None, None, None]:
    point = line.find(".assert_")

    if point != -1:
        end_pos = line[point:].find("(") + point
        return point, line[point + 1 : end_pos], line[:point]
    else:
        return None, None, None


@skip_ignored_lines  # type: ignore[untyped-decorator]
@core.flake8ext  # type: ignore[untyped-decorator]
def check_assert_methods_from_mock(
    logical_line: str, filename: str
) -> Generator[tuple[int, str], None, None]:
    """Ensure that ``assert_*`` methods from ``mock`` library is used correctly

    N301 - base error number
    N302 - related to nonexistent "assert_called"
    N303 - related to nonexistent "assert_called_once"
    """

    correct_names = [
        "assert_any_call",
        "assert_called_once_with",
        "assert_called_with",
        "assert_has_calls",
    ]
    ignored_files = ["./tests/unit/test_hacking.py"]

    if filename.startswith("./tests") and filename not in ignored_files:
        pos, method_name, obj_name = _parse_assert_mock_str(logical_line)

        if pos:
            if method_name not in correct_names:
                error_number = "N301"
                msg = (
                    "%(error_number)s:'%(method)s' is not present in `mock`"
                    " library. %(custom_msg)s For more details, visit "
                    "http://www.voidspace.org.uk/python/mock/ ."
                )

                if method_name == "assert_called":
                    error_number = "N302"
                    custom_msg = (
                        "Maybe, you should try to use "
                        f"'assertTrue({obj_name}.called)' instead."
                    )
                elif method_name == "assert_called_once":
                    # For more details, see a bug in Rally:
                    #    https://bugs.launchpad.net/rally/+bug/1305991
                    error_number = "N303"
                    custom_msg = (
                        "Maybe, you should try to use "
                        f"'assertEqual(1, {obj_name}.call_count)' "
                        f"or '{obj_name}.assert_called_once_with()'"
                        " instead."
                    )
                else:
                    custom_msg = "Correct 'assert_*' methods: '{}'.".format(
                        "', '".join(correct_names)
                    )

                yield (
                    pos,
                    msg
                    % {
                        "error_number": error_number,
                        "method": method_name,
                        "custom_msg": custom_msg,
                    },
                )


def _check_triple(line: str, i: int, char: str) -> bool:
    return i + 2 < len(line) and (
        char == line[i] == line[i + 1] == line[i + 2]
    )


@skip_ignored_lines  # type: ignore[untyped-decorator]
@core.flake8ext  # type: ignore[untyped-decorator]
def check_quotes(
    logical_line: str, filename: str
) -> Generator[tuple[int, str], None, None]:
    """Check that single quotation marks are not used

    N350
    """

    in_string = False
    in_multiline_string = False
    single_quotas_are_used = False

    i = 0
    while i < len(logical_line):
        char = logical_line[i]

        if in_string:
            if char == "\"":
                in_string = False
            if char == "\\":
                i += 1  # ignore next char

        elif in_multiline_string:
            if _check_triple(logical_line, i, "\""):
                i += 2  # skip next 2 chars
                in_multiline_string = False

        elif char == "#":
            break

        elif char == "'":
            single_quotas_are_used = True
            break

        elif char == "\"":
            if _check_triple(logical_line, i, "\""):
                in_multiline_string = True
                i += 3
                continue
            in_string = True

        i += 1

    if single_quotas_are_used:
        yield (i, "N350 Remove Single quotes")


@skip_ignored_lines  # type: ignore[untyped-decorator]
@core.flake8ext  # type: ignore[untyped-decorator]
def check_no_constructor_data_struct(
    logical_line: str, filename: str
) -> Generator[tuple[int, str], None, None]:
    """Check that data structs (lists, dicts) are declared using literals

    N351
    """

    match = re_no_construct_dict.search(logical_line)
    if match:
        yield (0, "N351 Remove dict() construct and use literal {}")
    match = re_no_construct_list.search(logical_line)
    if match:
        yield (0, "N351 Remove list() construct and use literal []")


@core.flake8ext  # type: ignore[untyped-decorator]
def check_dict_formatting_in_string(
    logical_line: str, tokens: Any
) -> Generator[tuple[int, str], None, None]:
    """Check that strings do not use dict-formatting with a single replacement

    N352
    """
    # NOTE(stpierre): Can't use @skip_ignored_lines here because it's
    # a stupid decorator that only works on functions that take
    # (logical_line, filename) as arguments.
    if (
        not logical_line
        or logical_line.startswith("#")
        or logical_line.endswith("# noqa")
    ):
        return

    current_string = ""
    in_string = False
    for token_type, text, start, end, line in tokens:
        if token_type == tokenize.STRING:
            if not in_string:
                current_string = ""
                in_string = True
            current_string += text.strip("\"")
        elif token_type == tokenize.OP:
            if not current_string:
                continue
            # NOTE(stpierre): The string formatting operator % has
            # lower precedence than +, so we assume that the logical
            # string has concluded whenever we hit an operator of any
            # sort. (Most operators don't work for strings anyway.)
            # Some string operators do have higher precedence than %,
            # though, so you can technically trick this check by doing
            # things like:
            #
            #     "%(foo)s" * 1 % {"foo": 1}
            #     "%(foo)s"[:] % {"foo": 1}
            #
            # It also will produce false positives if you use explicit
            # parenthesized addition for two strings instead of
            # concatenation by juxtaposition, e.g.:
            #
            #     ("%(foo)s" + "%(bar)s") % vals
            #
            # But if you do any of those things, then you deserve all
            # of the horrible things that happen to you, and probably
            # many more.
            in_string = False
            if text == "%":
                format_keys = set()
                for match in re_str_format.finditer(current_string):
                    format_keys.add(match.group(1))
                if len(format_keys) == 1:
                    yield (
                        0,
                        "N352 Do not use mapping key string formatting "
                        "with a single key",
                    )
            if text != ")":
                # NOTE(stpierre): You can have a parenthesized string
                # followed by %, so a closing paren doesn't obviate
                # the possibility for a substitution operator like
                # every other operator does.
                current_string = ""
        elif token_type in (tokenize.NL, tokenize.COMMENT):
            continue
        else:
            in_string = False
            if token_type == tokenize.NEWLINE:
                current_string = ""


@core.flake8ext  # type: ignore[untyped-decorator]
def check_raises(physical_line: str, filename: str) -> tuple[int, str] | None:
    """Check raises usage

    N354
    """

    ignored_files = [
        "./tests/unit/test_hacking.py",
        "./tests/hacking/checks.py",
    ]
    if filename not in ignored_files:
        if re_raises.search(physical_line):
            return (
                0,
                "N354 ':Please use ':raises Exception: conditions' "
                "in docstrings.",
            )
    return None
