from __future__ import annotations

import os
import re
import json
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


def process_raw_assignment_block(line_block, target_type, content, cont):
    type_match = None

    if not cont:
        type_match = (
            line_block if re.match(rf"^\s*{target_type}\s*=\s*", line_block) else None
        )

    if type_match or cont == target_type:
        if cont and content:
            content += "\n" + line_block.rstrip()
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


_RE_VAR_HEADER = re.compile(r'\s*variable\s+"?([^"]+)"?\s*{\s*', re.DOTALL)


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


def _is_expression_string(value: str) -> bool:
    stripped = value.strip()
    return stripped.startswith("${") and stripped.endswith("}")


def _unwrap_expression(value: str) -> str:
    stripped = value.strip()
    return stripped[2:-1] if _is_expression_string(stripped) else stripped


def _format_hcl_key(key) -> str:
    if isinstance(key, str):
        return json.dumps(key)
    return str(key)


def normalize_hcl_string(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        if stripped[0] == '"':
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return stripped[1:-1]
        return stripped[1:-1]
    return value


def hcl_value_to_string(value, treat_plain_string_as_expression: bool = False) -> str:
    if value is None:
        return "null"

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, str):
        value = normalize_hcl_string(value)
        if _is_expression_string(value):
            return _unwrap_expression(value)
        if treat_plain_string_as_expression:
            return value.strip()
        return json.dumps(value)

    if isinstance(value, list):
        return "[" + ",".join(hcl_value_to_string(item) for item in value) + "]"

    if isinstance(value, dict):
        parts = [
            f"{_format_hcl_key(key)} = {hcl_value_to_string(item)}"
            for key, item in value.items()
        ]
        return "{" + ",".join(parts) + "}"

    return str(value)


def construct_validation_blocks(validation_value) -> str:
    if not validation_value:
        return ""

    validation_blocks = (
        validation_value
        if isinstance(validation_value, list)
        else [validation_value]
    )

    rendered_blocks = []
    for block in validation_blocks:
        if not isinstance(block, dict):
            continue

        lines = ["  validation {"]
        if "condition" in block:
            lines.append(
                "    condition = "
                + hcl_value_to_string(
                    block["condition"], treat_plain_string_as_expression=True
                )
            )
        if "error_message" in block:
            lines.append(
                "    error_message = " + hcl_value_to_string(block["error_message"])
            )

        for key, value in block.items():
            if key in {"condition", "error_message"}:
                continue
            lines.append(f"    {key} = {hcl_value_to_string(value)}")

        lines.append("  }")
        rendered_blocks.append("\n".join(lines))

    return "\n".join(rendered_blocks)


def extract_type_overrides(file_content: str) -> dict[str, str]:
    overrides: dict[str, str] = {}
    metadata = extract_variable_metadata(file_content)
    for name, item in metadata.items():
        type_override = item.get("type_override")
        if type_override:
            overrides[name] = type_override

    return overrides


def extract_validation_blocks(file_content: str) -> dict[str, str]:
    validations: dict[str, str] = {}
    metadata = extract_variable_metadata(file_content)
    for name, item in metadata.items():
        validation = item.get("validation")
        if validation:
            validations[name] = validation

    return validations


def extract_default_blocks(file_content: str) -> dict[str, str]:
    defaults: dict[str, str] = {}
    metadata = extract_variable_metadata(file_content)
    for name, item in metadata.items():
        default = item.get("default_block")
        if default is not None:
            defaults[name] = default

    return defaults


def extract_variable_metadata(file_content: str) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    block = []
    match_flag = False
    name = None

    for line in file_content.split("\n"):
        block.append(line)
        match = _RE_VAR_HEADER.match(line)
        if match and not match_flag:
            name = match.group(1)
            match_flag = True

        if count_blocks(block) and match_flag:
            match_flag = False
            type_override = None
            type_override_cont = None
            default_block = ""
            default_block_cont = None
            validation = ""
            validation_cont = None

            for line_block in block:
                type_override, type_override_cont = process_line_block(
                    line_block,
                    "type_override",
                    type_override,
                    type_override_cont,
                )
                default_block, default_block_cont = process_raw_assignment_block(
                    line_block,
                    "default",
                    default_block,
                    default_block_cont,
                )
                validation, validation_cont = process_named_block(
                    line_block,
                    "validation",
                    validation,
                    validation_cont,
                )

            if name:
                item: dict[str, str] = {}
                if type_override:
                    item["type_override"] = type_override
                if default_block:
                    item["default_block"] = default_block
                if validation:
                    item["validation"] = validation
                if item:
                    metadata[name] = item

            block = []

    return metadata


def construct_tf_variable(content, default_blocks: dict[str, str] | None = None):
    name = content["name"]
    type_str = content["type"].strip()
    desc_str = content["description"].strip()
    has_default = "default" in content
    default_str = content.get("default", "").strip()
    default_block_str = (default_blocks or {}).get(name, "").strip()
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
        if default_block_str:
            default_lines = default_block_str.splitlines()
            if len(default_lines) == 1:
                lines.append(f"  default = {default_lines[0].strip()}")
            else:
                lines.append(f"  default = {default_lines[0].strip()}")
                lines.extend(line.rstrip() for line in default_lines[1:])
        elif default_str == "{}":
            lines.append("  default = {}")
        else:
            lines.append(f"  default = {format_block(default_str, inline=True)}")

    if validation_str:
        lines.append(indent_block(validation_str, indent_level=1))

    lines.append("}\n\n")
    return "\n".join(lines)


def construct_tf_file(content, default_blocks: dict[str, str] | None = None):
    parts = (construct_tf_variable(item, default_blocks=default_blocks) for item in content)
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
