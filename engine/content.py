import copy
import hashlib
import json
import re
from html import unescape
from html.parser import HTMLParser


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def payload(question):
    return question[question["questionType"]]


def read_field(question, field):
    return question["questionType"] if field == "questionType" else payload(question)[field]


def text(html):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]*>", " ", html))).strip()


def title(question):
    return text(payload(question)["question"]).split("(A)")[0][:130]


def apply_patches(question, patches):
    """Apply one atomic proposal to a copy, using the original active payload."""
    result = copy.deepcopy(question)
    old_type = result["questionType"]
    for patch in patches:
        field, find, replacement = patch["field"], patch["find"], patch["replace"]
        container = result if field == "questionType" else result[old_type]
        current = container[field]
        if field in ("answer", "questionType"):
            if current != find:
                raise ValueError("Stale field value")
            container[field] = replacement
        else:
            if not isinstance(find, str) or not find or current.count(find) != 1:
                raise ValueError("Patch must match exactly once")
            container[field] = current.replace(find, replacement, 1)
    new_type = result["questionType"]
    if new_type != old_type:
        result[new_type] = result.pop(old_type)
    return result


class MathShape(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag == "math" or self.stack:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if self.stack:
            if self.stack[-1] != tag:
                self.errors.append("Mismatched MathML tag: " + tag)
            else:
                self.stack.pop()


def math_errors(value):
    parser = MathShape()
    parser.feed(value)
    return len(parser.errors) + len(parser.stack)
