import os
import sys
from io import StringIO
from typing import List, Dict, Optional, TypedDict

import hcl2
from rich.console import Console

from tfdocs.utils import (
    construct_validation_blocks,
    construct_tf_file,
    extract_default_blocks,
    extract_type_overrides,
    extract_validation_blocks,
    generate_source,
    hcl_value_to_string,
    normalize_hcl_string,
)


class VariableItem(TypedDict, total=False):
    name: str
    type_override: Optional[str]
    type: str
    description: str
    default: str
    validation: str


class Readme:
    def __init__(
        self,
        readme_file: str,
        variables_file: str,
        module_name: Optional[str] = None,
        module_source: Optional[str] = None,
        module_source_git: bool = False,
    ) -> None:
        self.module_name: Optional[str] = module_name
        self.module_source: Optional[str] = module_source
        self.module_source_git: bool = module_source_git
        self.readme_content: str  # populated lazily via construct_readme()
        self.readme_changed: bool = True
        self.variables_changed: bool = True
        self.readme_file: str = readme_file
        self.variables_file: str = variables_file
        self.str_len: int = 0
        self.console = Console()
        self.variables: List[VariableItem] = []

        try:
            with open(self.variables_file, "r") as file:
                file_content = file.read().strip()
            parsed_content = hcl2.load(StringIO(file_content))
            type_overrides = extract_type_overrides(file_content)
            self.default_blocks = extract_default_blocks(file_content)
            validation_blocks = extract_validation_blocks(file_content)

            for variable_block in parsed_content.get("variable", []):
                if not isinstance(variable_block, dict):
                    continue

                for name, body in variable_block.items():
                    if isinstance(name, str):
                        name = normalize_hcl_string(name)
                    if not isinstance(body, dict):
                        body = {}

                    type_override = type_overrides.get(name)
                    type_content = hcl_value_to_string(
                        body.get("type", "unknown"),
                        treat_plain_string_as_expression=True,
                    )
                    description_raw = body.get("description")
                    description_content = (
                        hcl_value_to_string(description_raw)
                        if description_raw is not None
                        else '"No description provided"'
                    )
                    validation_content = validation_blocks.get(name) or construct_validation_blocks(
                        body.get("validation")
                    )

                    type_len_content = type_override if type_override else type_content
                    candidate_len = len(f"  {name} = <{type_len_content}>")
                    if candidate_len > self.str_len:
                        self.str_len = candidate_len

                    attributes: VariableItem = {
                        "name": name,
                        "type_override": type_override,
                        "type": type_content if type_content else "unknown",
                        "description": description_content,
                    }

                    if "default" in body:
                        attributes["default"] = hcl_value_to_string(body["default"])
                    if validation_content:
                        attributes["validation"] = validation_content

                    self.variables.append(attributes)

            self.sorted_variables: List[VariableItem] = sorted(
                self.variables, key=lambda k: k["name"]
            )

            if construct_tf_file(self.sorted_variables, self.default_blocks).strip() == file_content.strip():
                self.variables_changed = False

        except FileNotFoundError:
            self.console.print(
                f"[red]ERROR:[/] Cannot find {self.variables_file} in current directory"
            )
            sys.exit(-1)

    def write_variables(self) -> None:
        with open(self.variables_file, "w") as file:
            file.writelines(construct_tf_file(self.sorted_variables, self.default_blocks))

    def print_variables_file(self) -> None:
        self.console.print("[purple]--- variables.tf ---[/]")
        print(construct_tf_file(self.sorted_variables, self.default_blocks))

    def get_status(self) -> Dict[str, bool]:
        return {
            "readme": self.readme_changed,
            "variables": self.variables_changed,
        }

    def construct_readme(self) -> List[str]:
        readme_content: List[str] = [
            "```",
            f"module <{self.module_name}> {{",
            f'  source = "{generate_source(self.module_name, self.module_source, self.module_source_git)}"',
        ]

        for item in self.sorted_variables:
            type_str = (
                item["type_override"] if item.get("type_override") else item["type"]
            )
            spaces = " " * (self.str_len - len(f"  {item['name']} = <{type_str}>") + 2)
            desc_raw = item["description"]
            description = (
                desc_raw[1:-1]
                if (desc_raw.startswith('"') or desc_raw.startswith("'"))
                and (desc_raw.endswith('"') or desc_raw.endswith("'"))
                else desc_raw
            )

            readme_content.append(
                f"  {item['name']} = <{type_str.upper()}> {spaces} # {description}"
            )

        readme_content.append("}")
        readme_content.append("```")

        if os.path.exists(self.readme_file):
            with open(self.readme_file, "r") as file:
                content = file.read()

            lines = content.split("\n")
            start_index: Optional[int] = None
            end_index: Optional[int] = None

            for i, line in enumerate(lines):
                if "<!-- TFDOCS START -->" in line:
                    start_index = i
                elif "<!-- TFDOCS END -->" in line:
                    end_index = i

            lines_constructed = lines[:]
            if start_index is not None and end_index is not None:
                del lines_constructed[start_index + 1 : end_index]
                lines_constructed[start_index + 1 : start_index + 1] = readme_content

                # Check if the README.md file has changed
                if lines_constructed == lines:
                    self.readme_changed = False

                return lines_constructed

        return (
            [f"# {self.module_name} module", "", "<!-- TFDOCS START -->"]
            + readme_content
            + ["<!-- TFDOCS END -->", ""]
        )

    def print_readme(self) -> None:
        self.console.print("[purple]--- README.md ---[/]")
        for line in self.construct_readme():
            print(line)

    def write_readme(self) -> bool:
        readme_content = self.construct_readme()

        if readme_content and readme_content[-1] == "":
            readme_content.pop()

        with open(self.readme_file, "w") as file:
            file.writelines("%s\n" % item for item in readme_content)
        return True
