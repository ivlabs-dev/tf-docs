import os
import re
import git


def count_blocks(data):
    s = "".join(data) if isinstance(data, list) else data
    opens = {"{": "}", "(": ")", "[": "]"}
    closes = {v: k for k, v in opens.items()}
    stack = []

    in_string = False
    esc = False

    for ch in s:
        if ch == '"' and not esc:
            in_string = not in_string
        esc = (ch == "\\") and not esc
        if in_string:
            continue

        if ch in opens:
            stack.append(ch)
        elif ch in closes:
            if not stack or stack[-1] != closes[ch]:
                return False  # early exit on mismatch
            stack.pop()

    return not stack


def process_line_block(line_block, target_type, content, cont):
    type_match = None

    if target_type == "type_override":
        target_type = r"#\s*tfdocs:\s*type"

    if not cont:
        type_match = (
            line_block if re.match(rf"^\s*{target_type}\s*=\s*", line_block) else None
        )

    if type_match or cont == target_type:
        if cont:
            content += line_block.strip()
        else:
            content = line_block.split("=", 1)[1].strip()

        if not count_blocks(content):
            cont = target_type
        else:
            cont = None

    return content, cont


def process_named_block(line_block, target_type, content, cont):
    block_match = None

    if not cont:
        block_match = (
            line_block if re.match(rf"^\s*{target_type}\s*{{", line_block) else None
        )

    if block_match or cont == target_type:
        if cont and content:
            content += "\n" + line_block.rstrip()
        else:
            content = line_block.rstrip()

        if not count_blocks(content):
            cont = target_type
        else:
            cont = None

    return content, cont


_TYPE_CONSTRUCTORS_RE = re.compile(r"\b(list|set|map|object|tuple)\b")


def match_type_constructors(string):
    return _TYPE_CONSTRUCTORS_RE.search(string) is not None


def format_block(input_str: str, indent_level: int = 0, inline: bool = False) -> str:
    input_str = input_str.strip()
    indent = "  " * indent_level

    if input_str.startswith("{") and input_str.endswith("}"):
        return format_map(input_str[1:-1], indent_level, inline)

    if input_str.startswith("[") and input_str.endswith("]"):
        return format_list(input_str[1:-1], indent_level)

    if "(" in input_str and input_str.endswith(")"):
        return format_function_call(input_str, indent_level, inline)

    return indent + input_str


def smart_split(s):
    result = []
    current = ""
    depth = 0
    in_string = False

    for char in s:
        if char == '"' and not current.endswith("\\"):
            in_string = not in_string
        if not in_string:
            if char in "{[(":
                depth += 1
            elif char in "}])":
                depth -= 1
        if char == "," and depth == 0 and not in_string:
            result.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        result.append(current.strip())
    return result


def format_map(content: str, indent_level: int, inline: bool = False) -> str:
    if inline and content.strip() == "":
        return "{}"

    if inline:
        body_indent = "  " * (indent_level + 2)
        closing_indent = "  " * (indent_level + 1)
    else:
        body_indent = "  " * (indent_level + 1)
        closing_indent = "  " * indent_level

    parts = smart_split(content)
    kv_parts = [p for p in parts if "=" in p]

    lines = []
    for i, part in enumerate(kv_parts):
        key, val = map(str.strip, part.split("=", 1))
        formatted_val = format_block(val, indent_level + 1, inline=True).strip()
        comma = "," if i < len(kv_parts) - 1 else ""
        lines.append(f"{body_indent}{key} = {formatted_val}{comma}")

    return "{\n" + "\n".join(lines) + f"\n{closing_indent}}}"


def format_list(content: str, indent_level: int) -> str:
    opening_indent = "  " * indent_level
    closing_indent = "  " * (indent_level + 1)

    items = smart_split(content)
    if not items:
        return f"{opening_indent}[]"

    rendered_items = []
    for i, raw_item in enumerate(items):
        formatted = format_block(raw_item, indent_level + 1).rstrip()
        lines = formatted.splitlines()

        if len(lines) > 1:
            adjusted = []
            for idx, line in enumerate(lines):
                if idx == 0:
                    target = indent_level + 2
                elif idx == len(lines) - 1:
                    target = indent_level + 2
                else:
                    target = indent_level + 3
                adjusted.append(("  " * target) + line.strip())
            item_block = "\n".join(adjusted)
        else:
            item_block = ("  " * (indent_level + 2)) + lines[0].strip()

        comma = "," if (len(items) > 1 and i < len(items) - 1) else ""
        rendered_items.append(item_block + comma)

    return f"{opening_indent}[\n" + "\n".join(rendered_items) + f"\n{closing_indent}]"


def format_function_call(content: str, indent_level: int, inline: bool = False) -> str:
    match = re.match(r"^(\w+)\((.*)\)$", content.strip(), re.DOTALL)
    if not match:
        return "  " * indent_level + content

    func_name, inner = match.groups()
    inner = inner.strip()

    if inner.startswith("{") and inner.endswith("}"):
        adjusted_level = indent_level - 1 if inline else indent_level
        formatted = format_block(inner, max(adjusted_level, 0), inline=True).strip()
        return f"{func_name}({formatted})"

    if inner.startswith("[") and inner.endswith("]"):
        formatted = format_block(inner, indent_level).strip()
        return f"{func_name}({formatted})"

    parts = smart_split(inner)

    if inline and len(parts) == 1 and re.match(r"^\w+\(.*\)$", parts[0].strip()):
        formatted_parts = [
            format_block(parts[0], max(indent_level - 1, 0), inline=True).strip()
        ]
    else:
        formatted_parts = [
            format_block(part, indent_level + 1).strip() for part in parts
        ]

    joined = ", ".join(formatted_parts)
    return f"{func_name}({joined})"


def indent_block(content: str, indent_level: int = 0) -> str:
    lines = content.strip("\n").splitlines()
    if not lines:
        return ""

    non_empty_lines = [line for line in lines if line.strip()]
    common_indent = min(
        len(line) - len(line.lstrip()) for line in non_empty_lines
    ) if non_empty_lines else 0
    indent = "  " * indent_level

    return "\n".join(
        f"{indent}{line[common_indent:]}" if line.strip() else ""
        for line in lines
    )


def construct_tf_variable(content):
    name = content["name"]
    type_str = content["type"].strip()
    desc_str = content["description"].strip()
    has_default = "default" in content
    default_str = content.get("default", "").strip()
    validation_str = content.get("validation", "")

    lines = [f'variable "{name}" {{']

    if content["type_override"]:
        lines.append(f"  #tfdocs: type={content['type_override'].strip()}")

    desc_first = type_str.startswith("map(object(") and default_str == "{}"

    if desc_first:
        lines.append(f"  description = {desc_str}")
        lines.append(f"  type = {format_block(type_str, inline=True)}")
    else:
        lines.append(f"  type = {format_block(type_str, inline=True)}")
        lines.append(f"  description = {desc_str}")

    if has_default:
        if default_str == "{}":
            lines.append("  default = {}")
        else:
            lines.append(f"  default = {format_block(default_str, inline=True)}")

    if validation_str:
        lines.append(indent_block(validation_str, indent_level=1))

    lines.append("}\n\n")
    return "\n".join(lines)


def construct_tf_file(content):
    parts = (construct_tf_variable(item) for item in content)
    return "".join(parts).rstrip() + "\n"


def generate_source(module_name, source, source_git):
    if source and not source_git:
        return source
    try:
        repo = git.Repo(search_parent_directories=True)
        repo_root = repo.working_tree_dir or repo.git.rev_parse("--show-toplevel")
        rel_path = os.path.relpath(os.getcwd(), repo_root)
        base = source or repo.remotes.origin.url
        return f"{base}//{rel_path}?ref=<TAG>"
    except git.exc.InvalidGitRepositoryError:
        return f"./modules/{module_name}"
