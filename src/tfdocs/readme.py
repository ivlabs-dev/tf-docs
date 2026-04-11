import os
import re
import sys
from typing import List, Dict, Optional, TypedDict

from rich.console import Console

from tfdocs.utils import (
    count_blocks,
    construct_tf_file,
    generate_source,
    process_line_block,
    process_named_block,
)


class VariableItem(TypedDict, total=False):
    name: str
    type_override: Optional[str]
    type: str
    description: str
    default: str
    validation: str


class Readme:
    _re_var_header = re.compile(r'\s*variable\s+"?(\w+)"?\s*{\s*', re.DOTALL)

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

            block: List[str] = []
            match_flag = False
            name: Optional[str] = None

            for line in file_content.split("\n"):
                block.append(line)
                match = self._re_var_header.match(line)
                if match and not match_flag:
                    name = match.group(1)
                    match_flag = True

                if count_blocks(block) and match_flag:
                    match_flag = False
                    (
                        type_content,
                        default_content,
                        description_content,
                        type_override,
                        validation_content,
                    ) = ("", "", "", None, "")
                    type_cont = None
                    type_override_cont = None
                    default_cont = None
                    description_cont = None
                    validation_cont = None

                    for line_block in block:
                        type_content, type_cont = process_line_block(
                            line_block, "type", type_content, type_cont
                        )

                        type_override, type_override_cont = process_line_block(
                            line_block,
                            "type_override",
                            type_override,
                            type_override_cont,
                        )

                        type_len_content = (
                            type_override if type_override else type_content
                        )
                        if name and type_len_content:
                            candidate_len = len(f"  {name} = <{type_len_content}>")
                            if candidate_len > self.str_len:
                                self.str_len = candidate_len

                        default_content, default_cont = process_line_block(
                            line_block, "default", default_content, default_cont
                        )
                        description_content, description_cont = process_line_block(
                            line_block,
                            "description",
                            description_content,
                            description_cont,
                        )
                        validation_content, validation_cont = process_named_block(
                            line_block,
                            "validation",
                            validation_content,
                            validation_cont,
                        )

                    block = []
                    attributes: VariableItem = {
                        "name": name or "",
                        "type_override": type_override,
                        "type": type_content if type_content else "unknown",
                        "description": description_content
                        if description_content
                        else '"No description provided"',
                    }

                    if default_content:
                        attributes["default"] = default_content
                    if validation_content:
                        attributes["validation"] = validation_content

                    self.variables.append(attributes)

            self.sorted_variables: List[VariableItem] = sorted(
                self.variables, key=lambda k: k["name"]
            )

            if construct_tf_file(self.sorted_variables).strip() == file_content.strip():
                self.variables_changed = False

        except FileNotFoundError:
            self.console.print(
                f"[red]ERROR:[/] Cannot find {self.variables_file} in current directory"
            )
            sys.exit(-1)

    def write_variables(self) -> None:
        with open(self.variables_file, "w") as file:
            file.writelines(construct_tf_file(self.sorted_variables))

    def print_variables_file(self) -> None:
        self.console.print("[purple]--- variables.tf ---[/]")
        print(construct_tf_file(self.sorted_variables))

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
