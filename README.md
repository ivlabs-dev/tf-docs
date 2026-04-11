# TF-Docs

`tfdocs` lets you generate `README.md` for Terraform modules based on `variables.tf`.
Additionally, it can sort variable definitions.

# Usage

    tfdocs [flags] <variables.tf>

#### Flags:

    -h, --help            Show this help message and exit
    --name, -n            Specify a custom name for the module
    --readme              Specify the name of the output file (default: README.md)
    --variables           Specify the name of the file containing variables (default: variables.tf)
    --source SOURCE       Specify a custom source for the module
    --git-source          Only to be used together with --source to specify the source is a git repository. If true, sub directory and a place holder TAG will be appended to the source
    -f                    Format and sort variables.tf file
    --dry-run             Show the output without writing to the file
    --version

## Input file
**Default:** `variables.tf`

All the input variables of the module must be defined in a single file. By default `tfdocs` will look for a file
named `variables.tf` in the current directory. Alternatively a custom file can be specified using the `--variables`
flag.

### Example

**variables.tf**

```hcl
variable "my_string" {
  type = string
  description = "Description of the string"
  default = "default"
}

variable "my_list" {
  type = List(string)
  description = "Description of the list"
  default = ["default"]
}
```

#### Format `variables.tf`

You can use the `-f` flag to format the `variables.tf` file. This will sort the variables in alphabetical order.

## Generated Readme file
**Default:** `README.md`

The module expects to have a `README.md` file in the current directory. If the file does not exist, `tfdocs` will create
one. Alternatively, a custom file can be specified using the `--readme` flag.

### Example

**README.md**

```markdown
# My module

Insert a description of the module here.

<!-- TFDOCS START -->
module <my_module> {
source = "git@github.com:<your_name>/<your_repo>.git//<subfolder>?ref=<TAG>"
my_list = <LIST(STRING)>    # Description of the list
my_string = <STRING>        # Description of the string
}
<!-- TFDOCS END -->

Custom content
```

`tfdocs` replaces only the content between the markers below with variable definitions from `variables.tf`.

Markers:
`<!-- TFDOCS START -->` and `<!-- TFDOCS END -->`

## Module Source
**Default:** `git-remote-origin//<subfolder>?ref=<TAG>`

By default, if the module is in a Git repository, `tfdocs` will utilize the remote origin to generate the source URL
(`git://github.com/<your_name>/<your_repo>.git//<subfolder>?ref=<TAG>`). 

Otherwise, either the source URL can be specified using the `--source` flag or if not provided it will default
to `./modules/{CURRENT_DIRECTORY}`.


## Annotations
### Override variable type

Use `#tfdocs: type=<TYPE>` to override the variable type. This is useful when the type is not correctly inferred from the variable definition or when you want to customize it.

### Example

**variables.tf**

```hcl
variable "my_object" {
  #tfdocs: type = list(object)
  type = list(object({
    name = string
    size = number
    directory = string
  }))
  description = "Description of the string"
  default = "default"
}
```

> **Note**: `tfdocs` overwrite an existing README.md file. It's always good to use `--dry-run` first.

# Authors

`tfdocs` is created and maintained by [ivlabs].

[ivlabs]: https://github.com/ivlabs-dev/tf-docs
