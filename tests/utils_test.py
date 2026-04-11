from tfdocs import utils


def test_count_blocks():
    assert utils.count_blocks("()") is True
    assert utils.count_blocks("()(") is False
    assert utils.count_blocks("()()") is True
    assert utils.count_blocks("()()(") is False
    assert utils.count_blocks("{}") is True
    assert utils.count_blocks("{}{") is False
    assert utils.count_blocks("{}{}") is True
    assert utils.count_blocks("{}{}{") is False
    assert utils.count_blocks("[]") is True
    assert utils.count_blocks("[][") is False
    assert utils.count_blocks("[][]") is True
    assert utils.count_blocks("[][][") is False
    assert utils.count_blocks("a > b") is True
    assert utils.count_blocks("a < b") is True
    assert utils.count_blocks("(a > b) && (c < d)") is True
    assert utils.count_blocks("(){}[]") is True
    assert utils.count_blocks("({[]})") is True
    assert utils.count_blocks("({[]})(") is False
    assert utils.count_blocks("({[]})()") is True
    assert utils.count_blocks("({[]})()(") is False
    assert utils.count_blocks("({[]})(){}") is True
    assert utils.count_blocks("({[]})(){}{") is False
    assert utils.count_blocks("({[]})(){}{}") is True
    assert utils.count_blocks(["()"]) is True
    assert utils.count_blocks(["()","("]) is False
    assert utils.count_blocks(["()","()"]) is True
    assert utils.count_blocks(["()","()","("]) is False
    assert utils.count_blocks(["{}"]) is True
    assert utils.count_blocks(["{}","{"]) is False
    assert utils.count_blocks(["{}","{}"]) is True
    assert utils.count_blocks(["{}","{}","{"]) is False


def test_process_line_block():
    assert utils.process_line_block("type = string", "type", "", None) == (
        "string",
        None,
    )
    assert utils.process_line_block("typee = string", "type", "", None) == ("", None)
    assert utils.process_line_block("type = stringg", "type", "", None) == (
        "stringg",
        None,
    )
    assert utils.process_line_block("type = list[]", "type", "", None) == (
        "list[]",
        None,
    )
    assert utils.process_line_block("type = list[", "type", "", None) == (
        "list[",
        "type",
    )
    assert utils.process_line_block("type = list[()", "type", "", None) == (
        "list[()",
        "type",
    )
    assert utils.process_line_block("type = list[()]", "type", "", None) == (
        "list[()]",
        None,
    )
    assert utils.process_line_block(
        'description = "my description"', "description", "", None
    ) == ('"my description"', None)
    assert utils.process_line_block("default = 24", "default", "", None) == ("24", None)
    assert utils.process_line_block("default = [1,2,3]", "default", "", None) == (
        "[1,2,3]",
        None,
    )
    assert utils.process_line_block("default = [1,2,3", "default", "", None) == (
        "[1,2,3",
        "default",
    )
    assert utils.process_line_block("default = [\"123 abc:def.ghi -zyx\"]", "default", "[\"123 abc:def.ghi -zyx\"]", None) == (
        "[\"123 abc:def.ghi -zyx\"]",
        None
    )
    assert utils.process_line_block(
        "#tfdocs:type=object()", "type_override", "", None
    ) == ("object()", None)
    assert utils.process_line_block(
        "# tfdocs:type=object()", "type_override", "", None
    ) == ("object()", None)
    assert utils.process_line_block(
        "# tfdocs:type = object()", "type_override", "", None
    ) == ("object()", None)
    assert utils.process_line_block(
        "# tfdocs: type=object()", "type_override", "", None
    ) == ("object()", None)
    assert utils.process_line_block(
        "# tfdocs: type=object(", "type_override", "", None
    ) == ("object(", "#\\s*tfdocs:\\s*type")

    assert utils.process_line_block("  )]", "type", "type = list[(", "type") == (
        "type = list[()]",
        None,
    )


def test_process_named_block():
    assert utils.process_named_block("validation {", "validation", "", None) == (
        "validation {",
        "validation",
    )
    assert utils.process_named_block(
        '  error_message = "my error"', "validation", "validation {", "validation"
    ) == (
        'validation {\n  error_message = "my error"',
        "validation",
    )
    assert utils.process_named_block(
        "}", "validation", 'validation {\n  error_message = "my error"', "validation"
    ) == (
        'validation {\n  error_message = "my error"\n}',
        None,
    )


def test_hcl_value_to_string():
    assert utils.hcl_value_to_string(None) == "null"
    assert utils.hcl_value_to_string(True) == "true"
    assert utils.hcl_value_to_string(False) == "false"
    assert utils.hcl_value_to_string(42) == "42"
    assert utils.hcl_value_to_string("plain text") == '"plain text"'
    assert (
        utils.hcl_value_to_string("${list(string)}", treat_plain_string_as_expression=True)
        == "list(string)"
    )
    assert utils.hcl_value_to_string("list(string)", treat_plain_string_as_expression=True) == "list(string)"
    assert utils.hcl_value_to_string(["a", 1, None]) == '["a",1,null]'
    assert utils.hcl_value_to_string({"user1": ["tag1"]}) == '{"user1" = ["tag1"]}'


def test_construct_validation_blocks():
    validation = [
        {
            "condition": "${!(var.primary && !var.secondary) || (var.subnet_ids != null && length(var.subnet_ids) > 0)}",
            "error_message": "You must set subnet_ids when primary is true and secondary is false.",
        }
    ]
    expected = """  validation {
    condition = !(var.primary && !var.secondary) || (var.subnet_ids != null && length(var.subnet_ids) > 0)
    error_message = "You must set subnet_ids when primary is true and secondary is false."
  }"""
    assert utils.construct_validation_blocks(validation) == expected


def test_extract_type_overrides():
    content = """
variable "my_object" {
  # tfdocs: type = list(object)
  type = list(object({
    name = string
  }))
}
"""
    assert utils.extract_type_overrides(content) == {
        "my_object": "list(object)"
    }


def test_match_type_constructors():
    assert utils.match_type_constructors("list") is True
    assert utils.match_type_constructors("set") is True
    assert utils.match_type_constructors("map") is True
    assert utils.match_type_constructors("object") is True
    assert utils.match_type_constructors("tuple") is True
    assert utils.match_type_constructors("list[]") is True
    assert utils.match_type_constructors("set{}") is True
    assert utils.match_type_constructors("map{}") is True
    assert utils.match_type_constructors("object()") is True
    assert utils.match_type_constructors("tuple()") is True
    assert utils.match_type_constructors("list[") is True
    assert utils.match_type_constructors("set{") is True
    assert utils.match_type_constructors("map{") is True
    assert utils.match_type_constructors("object(") is True
    assert utils.match_type_constructors("tuple(") is True
    assert utils.match_type_constructors("list[()") is True
    assert utils.match_type_constructors("set{}(") is True
    assert utils.match_type_constructors("listt") is False
    assert utils.match_type_constructors("listt[()") is False
    assert utils.match_type_constructors("json") is False
    assert utils.match_type_constructors("const") is False
    assert utils.match_type_constructors("const ") is False
    assert utils.match_type_constructors("array") is False
    assert utils.match_type_constructors("dict") is False


def test_format_block():
    assert (
        utils.format_block("my default string")
        == "my default string"
    )

    var1in = '[{name = "name1",size = 10,directory = "dir1"},{name = "name2",size = 15,directory = "dir2"},{name = "name3",size = 20,directory = "dir3"}]'
    var1out = """[
    {
      name = "name1",
      size = 10,
      directory = "dir1"
    },
    {
      name = "name2",
      size = 15,
      directory = "dir2"
    },
    {
      name = "name3",
      size = 20,
      directory = "dir3"
    }
  ]"""
    assert utils.format_block(var1in) == var1out

    var2in = "list(object({name = string,size = number,directory = string}))"
    var2out = """list(object({
      name = string,
      size = number,
      directory = string
    }))"""
    assert utils.format_block(var2in) == var2out

    assert (
        utils.format_block('"myapp-1.1.1"') == '"myapp-1.1.1"'
    )
    assert utils.format_block("40") == "40"


def test_construct_tf_variable():
    var1in = {
        "name": "my_variable",
        "type_override": None,
        "type": "string",
        "description": '"My variable"',
        "default": '"my default"',
    }
    var1out = """variable "my_variable" {
  type = string
  description = "My variable"
  default = "my default"
}

"""
    assert utils.construct_tf_variable(var1in) == var1out

    var2in = {
        "name": "my_variable",
        "type_override": "list(object({}))",
        "type": "list(object({name = string,size = number,directory = string}))",
        "description": '"My variable"',
        "default": '[{name = "name1",size = 10,directory = "dir1"},{name = "name2",size = 15,directory = "dir2"},{name = "name3",size = 20,directory = "dir3"}]',
    }
    var2out = """variable "my_variable" {
  #tfdocs: type=list(object({}))
  type = list(object({
    name = string,
    size = number,
    directory = string
  }))
  description = "My variable"
  default = [
    {
      name = "name1",
      size = 10,
      directory = "dir1"
    },
    {
      name = "name2",
      size = 15,
      directory = "dir2"
    },
    {
      name = "name3",
      size = 20,
      directory = "dir3"
    }
  ]
}

"""
    assert utils.construct_tf_variable(var2in) == var2out

    var3in = {
        "name": "my_variable",
        "type_override": None,
        "type": "string  ",
        "description": '"My variable"',
        "default": '"my default"',
    }
    var3out = """variable "my_variable" {
  type = string
  description = "My variable"
  default = "my default"
}

"""
    assert utils.construct_tf_variable(var3in) == var3out

    var4in = {
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
    var4out = """variable "subnet_ids" {
  type = list(string)
  description = "List of subnet IDs where the Lambda function will have access. They have to have connectivity to the Loki endpoint"
  default = null
  validation {
    condition = !(var.primary && !var.secondary) || (var.subnet_ids != null && length(var.subnet_ids) > 0)
    error_message = "You must set subnet_ids when primary is true and secondary is false."
  }
}

"""
    assert utils.construct_tf_variable(var4in) == var4out


def test_construct_tf_file():
    var1in = [
        {
            "name": "my_var",
            "type_override": None,
            "type": "string",
            "description": '"My description 1"',
            "default": '"my-default-1"',
        }
    ]
    var1out = """variable "my_var" {
  type = string
  description = "My description 1"
  default = "my-default-1"
}
"""
    assert utils.construct_tf_file(var1in) == var1out

    var2in = [
        {
            "name": "my_var2",
            "type_override": None,
            "type": "string",
            "description": '"my-default-2"',
        }
    ]
    var2out = """variable "my_var2" {
  type = string
  description = "my-default-2"
}
"""
    assert utils.construct_tf_file(var2in) == var2out

    var3in = [
        {
            "name": "my_var_3",
            "type_override": None,
            "type": "bool",
            "description": '"My description 3"',
            "default": "true",
        }
    ]
    var3out = """variable "my_var_3" {
  type = bool
  description = "My description 3"
  default = true
}
"""
    assert utils.construct_tf_file(var3in) == var3out

    var4in = [
        {
            "name": "my_var_4",
            "type_override": None,
            "type": "number",
            "description": '"My description 4"',
            "default": "45",
        }
    ]
    var4out = """variable "my_var_4" {
  type = number
  description = "My description 4"
  default = 45
}
"""
    assert utils.construct_tf_file(var4in) == var4out

    var5in = [
        {
            "name": "my_var_5",
            "type_override": "list(object({}))",
            "type": "list(object({name = string,size = number,directory = string}))",
            "description": '"Volume size of EBS for Bamboo, Docker and Backup"',
            "default": '[{name = "name1",size = 10,directory = "dir1"},{name = "name2",size = 15,directory = "dir2"},{name = "name3",size = 20,directory = "dir3"}]',
        }
    ]
    var5out = """variable "my_var_5" {
  #tfdocs: type=list(object({}))
  type = list(object({
    name = string,
    size = number,
    directory = string
  }))
  description = "Volume size of EBS for Bamboo, Docker and Backup"
  default = [
    {
      name = "name1",
      size = 10,
      directory = "dir1"
    },
    {
      name = "name2",
      size = 15,
      directory = "dir2"
    },
    {
      name = "name3",
      size = 20,
      directory = "dir3"
    }
  ]
}
"""
    assert utils.construct_tf_file(var5in) == var5out

    var6in = [
        {
            "name": "my_var_6",
            "type_override": None,
            "type": "any",
            "description": '"My description 6"',
            "default": "[]",
        }
    ]
    var6out = """variable "my_var_6" {
  type = any
  description = "My description 6"
  default = []
}
"""
    assert utils.construct_tf_file(var6in) == var6out

    var7in = [
        {
            "name": "my_var",
            "type_override": None,
            "type": "string",
            "description": '"My description 1"',
            "default": '"my-default-1"',
        },
        {
            "name": "my_var2",
            "type_override": None,
            "type": "string",
            "description": '"my-default-2"',
        },
        {
            "name": "my_var_3",
            "type_override": None,
            "type": "bool",
            "description": '"My description 3"',
            "default": "true",
        },
        {
            "name": "my_var_4",
            "type_override": None,
            "type": "number",
            "description": '"My description 4"',
            "default": "45",
        },
        {
            "name": "my_var_5",
            "type_override": "list(object({}))",
            "type": "list(object({name = string,size = number,directory = string}))",
            "description": '"My description 5"',
            "default": '[{name = "name1",size = 10,directory = "dir1"},{name = "name2",size = 15,directory = "dir2"},{name = "name3",size = 20,directory = "dir3"}]',
        },
        {
            "name": "my_var_6",
            "type_override": None,
            "type": "any",
            "description": '"My description 6"',
            "default": "[]",
        },
    ]
    var7out = """variable "my_var" {
  type = string
  description = "My description 1"
  default = "my-default-1"
}

variable "my_var2" {
  type = string
  description = "my-default-2"
}

variable "my_var_3" {
  type = bool
  description = "My description 3"
  default = true
}

variable "my_var_4" {
  type = number
  description = "My description 4"
  default = 45
}

variable "my_var_5" {
  #tfdocs: type=list(object({}))
  type = list(object({
    name = string,
    size = number,
    directory = string
  }))
  description = "My description 5"
  default = [
    {
      name = "name1",
      size = 10,
      directory = "dir1"
    },
    {
      name = "name2",
      size = 15,
      directory = "dir2"
    },
    {
      name = "name3",
      size = 20,
      directory = "dir3"
    }
  ]
}

variable "my_var_6" {
  type = any
  description = "My description 6"
  default = []
}
"""
    assert utils.construct_tf_file(var7in) == var7out

    var8in = [
        {
            "name": "my_var",
            "type_override": None,
            "type": "map(object({var1 = string,var2 = list(string),var3 = string}))",
            "description": '"My description"',
            "default": "{}",
        }
    ]
    var8out = """variable "my_var" {
  description = "My description"
  type = map(object({
    var1 = string,
    var2 = list(string),
    var3 = string
  }))
  default = {}
}
"""
    assert utils.construct_tf_file(var8in) == var8out

    var9in = [
        {
            "name": "my_var",
            "type_override": None,
            "type": "map(object({ tags = list(string),vhosts = list(string)}))",
            "description": '"My Description"',
            "default": '{"user1"={tags=["tag1"],vhosts=["vh1"]},"user2"={tags=["tag2"],vhosts=["vh2"]}}',
        }
    ]
    var9out = """variable "my_var" {
  type = map(object({
    tags = list(string),
    vhosts = list(string)
  }))
  description = "My Description"
  default = {
    "user1" = {
      tags = [
        "tag1"
      ],
      vhosts = [
        "vh1"
      ]
    },
    "user2" = {
      tags = [
        "tag2"
      ],
      vhosts = [
        "vh2"
      ]
    }
  }
}
"""
    assert utils.construct_tf_file(var9in) == var9out

    var10in = [
        {
            "name": "my_var",
            "type_override": None,
            "type": "map(object({ tags = list(string),vhosts = list(string)}))",
            "description": '"My description"',
            "default": '{"monitor"={tags=["tag3"],vhosts=["vh1","vh2","vh3"]}}',
        }
    ]
    var10out = """variable "my_var" {
  type = map(object({
    tags = list(string),
    vhosts = list(string)
  }))
  description = "My description"
  default = {
    "monitor" = {
      tags = [
        "tag3"
      ],
      vhosts = [
        "vh1",
        "vh2",
        "vh3"
      ]
    }
  }
}
"""
    assert utils.construct_tf_file(var10in) == var10out


def test_generate_source():
    assert (
        utils.generate_source("modules", "git@git.com:tfdocs", True)
        == "git@git.com:tfdocs//.?ref=<TAG>"
    )
    assert utils.generate_source("modules", "tfdocs", False) == "tfdocs"
