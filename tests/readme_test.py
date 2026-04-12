from tfdocs import readme
from tfdocs import utils
import os
import pytest
import tempfile

mock_variables_tf = """
variable "var1" {
  type        = string
  description = "This is variable 1"
}

variable "var2" {
  type        = number
  default     = 42
  description = "This is variable 2"
}

variable "var3" {
  type        = number
  default     = 54
}

variable "var4" {
  type        = list(string)
  default     = ["123 abc:def.ghi -zyx"]
  description = "This is variable 4"
}

variable "var5" {
  type        = list(string)
  default     = ["v=abc1 include:abc.com include:abc.def.net -all"]
  description = "This is variable 5"
}
"""

# Mock data for README.md
mock_readme_md = """
# Example module

<!-- TFDOCS START -->
<!-- TFDOCS END -->
"""

@pytest.fixture
def temp_files():
    # Create temporary files for variables.tf and README.md
    temp_dir = tempfile.TemporaryDirectory()
    variables_file = os.path.join(temp_dir.name, "variables.tf")
    readme_file = os.path.join(temp_dir.name, "README.md")

    # Write mock data to these files
    with open(variables_file, "w") as f:
        f.write(mock_variables_tf)

    with open(readme_file, "w") as f:
        f.write(mock_readme_md)

    yield variables_file, readme_file

    # Cleanup
    temp_dir.cleanup()

def test_initialization(temp_files):
    variables_file, readme_file = temp_files
    rd = readme.Readme(readme_file, variables_file, module_name="example")

    assert rd.module_name == "example"
    assert rd.variables_file == variables_file
    assert rd.readme_file == readme_file
    assert len(rd.variables) == 5

def test_variable_parsing(temp_files):
    variables_file, readme_file = temp_files
    rd = readme.Readme(readme_file, variables_file)

    expected_variables = [
        {
            "name": "var1",
            "type_override": None,
            "type": "string",
            "description": '"This is variable 1"',
        },
        {
            "name": "var2",
            "type_override": None,
            "type": "number",
            "description": '"This is variable 2"',
            "default": "42",
        },
        {
            "name": "var3",
            "type_override": None,
            "type": "number",
            "description": '"No description provided"',
            "default": "54",
        },
        {
            "name": "var4",
            "type_override": None,
            "type": "list(string)",
            "description": '"This is variable 4"',
            "default": '["123 abc:def.ghi -zyx"]',
        },
        {
            "name": "var5",
            "type_override": None,
            "type": "list(string)",
            "description": '"This is variable 5"',
            "default": '["v=abc1 include:abc.com include:abc.def.net -all"]',
        },
    ]

    assert rd.variables == expected_variables

def test_write_variables(temp_files):
    variables_file, readme_file = temp_files
    rd = readme.Readme(readme_file, variables_file)

    rd.write_variables()

    with open(variables_file, "r") as f:
        content = f.read()

    assert content.strip() == utils.construct_tf_file(
        rd.sorted_variables, rd.default_blocks
    ).strip()

def test_construct_readme(temp_files):
    variables_file, readme_file = temp_files
    rd = readme.Readme(readme_file, variables_file, module_name="example", module_source="git@git.com:tfdocs")

    constructed_readme = rd.construct_readme()

    expected_readme_content = [
        "```",
        "module <example> {",
        '  source = "git@git.com:tfdocs"',
        '  var1 = <STRING>          # This is variable 1',
        '  var2 = <NUMBER>          # This is variable 2',
        '  var3 = <NUMBER>          # No description provided',
        '  var4 = <LIST(STRING)>    # This is variable 4',
        '  var5 = <LIST(STRING)>    # This is variable 5',
        "}",
        "```",
    ]

    assert all(line in constructed_readme for line in expected_readme_content)

def test_write_readme(temp_files):
    variables_file, readme_file = temp_files
    rd = readme.Readme(readme_file, variables_file, module_name="example", module_source="git@git.com:tfdocs")

    rd.write_readme()

    with open(readme_file, "r") as f:
        content = f.read()

    expected_readme_content = (
        "# Example module\n\n<!-- TFDOCS START -->\n```\nmodule <example> {\n  source = \"git@git.com:tfdocs\"\n  var1 = <STRING>          # This is variable 1\n  var2 = <NUMBER>          # This is variable 2\n  var3 = <NUMBER>          # No description provided\n  var4 = <LIST(STRING)>    # This is variable 4\n  var5 = <LIST(STRING)>    # This is variable 5\n}\n```\n<!-- TFDOCS END -->\n"
    )

    assert content.strip() == expected_readme_content.strip()


def test_validation_variable_round_trip():
    variable_with_validation = """
variable "subnet_ids" {
  type = list(string)
  description = "List of subnet IDs where the Lambda function will have access. They have to have connectivity to the Loki endpoint"
  default = null
  validation {
    condition = !(var.primary && !var.secondary) || (var.subnet_ids != null && length(var.subnet_ids) > 0)
    error_message = "You must set subnet_ids when primary is true and secondary is false."
  }
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        variables_file = os.path.join(temp_dir, "variables.tf")
        readme_file = os.path.join(temp_dir, "README.md")

        with open(variables_file, "w") as f:
            f.write(variable_with_validation)

        with open(readme_file, "w") as f:
            f.write(mock_readme_md)

        rd = readme.Readme(readme_file, variables_file)

        assert rd.variables == [
            {
                "name": "subnet_ids",
                "type_override": None,
                "type": "list(string)",
                "description": '"List of subnet IDs where the Lambda function will have access. They have to have connectivity to the Loki endpoint"',
                "default": "null",
                "validation": """  validation {
    condition = !(var.primary && !var.secondary) || (var.subnet_ids != null && length(var.subnet_ids) > 0)
    error_message = "You must set subnet_ids when primary is true and secondary is false."
  }""",
            }
        ]

        rd.write_variables()

        with open(variables_file, "r") as f:
            content = f.read()

        assert content.strip() == variable_with_validation.strip()


def test_nested_map_default_round_trip():
    variables_with_nested_map_defaults = """
variable "service_extra_users" {
  type = map(object({
    tags = list(string)
    vhosts = list(string)
  }))
  description = "Extra users"
  default = {
    "monitor" = {
      tags = [
        "monitoring"
      ]
      vhosts = [
        "imw",
        "papi",
        "capi",
        "webhooks"
      ]
    }
  }
}

variable "service_users" {
  type = map(object({
    tags = list(string)
    vhosts = list(string)
  }))
  description = "Users"
  default = {
    "public-api" = {
      tags = [
        "administrator"
      ]
      vhosts = [
        "papi"
      ]
    }
    "integrations" = {
      tags = [
        "administrator"
      ]
      vhosts = [
        "imw"
      ]
    }
    "webhooks" = {
      tags = [
        "administrator"
      ]
      vhosts = [
        "webhooks"
      ]
    }
  }
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        variables_file = os.path.join(temp_dir, "variables.tf")
        readme_file = os.path.join(temp_dir, "README.md")

        with open(variables_file, "w") as f:
            f.write(variables_with_nested_map_defaults)

        with open(readme_file, "w") as f:
            f.write(mock_readme_md)

        rd = readme.Readme(readme_file, variables_file)
        rd.write_variables()

        with open(variables_file, "r") as f:
            content = f.read()

        assert '\\"monitor\\"' not in content
        assert '"tags" =' not in content
        assert content.strip() == variables_with_nested_map_defaults.strip()


def test_inline_object_type_spacing_is_preserved_in_readme_output():
    variables_content = """
variable "service_users_compact" {
  type = map(object({authorizations = map(list(string)),name = string}))
  description = "Users compact"
  default = {}
}

variable "service_users_spaced" {
  type = map(object({tags = list(string), vhosts = list(string)}))
  description = "Users spaced"
  default = {}
}
"""

    with tempfile.TemporaryDirectory() as temp_dir:
        variables_file = os.path.join(temp_dir, "variables.tf")
        readme_file = os.path.join(temp_dir, "README.md")

        with open(variables_file, "w") as f:
            f.write(variables_content)

        with open(readme_file, "w") as f:
            f.write(mock_readme_md)

        rd = readme.Readme(readme_file, variables_file, module_name="example")

        assert rd.variables[0]["type"] == 'map(object({authorizations = map(list(string)),name = string}))'
        assert rd.variables[1]["type"] == 'map(object({tags = list(string), vhosts = list(string)}))'
        assert any(
            'service_users_compact = <MAP(OBJECT({AUTHORIZATIONS = MAP(LIST(STRING)),NAME = STRING}))>'
            in line
            for line in rd.construct_readme()
        )
        assert any(
            'service_users_spaced = <MAP(OBJECT({TAGS = LIST(STRING), VHOSTS = LIST(STRING)}))>'
            in line
            for line in rd.construct_readme()
        )
