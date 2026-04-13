from tfdocs.cli import get_parser, Options, get_version


def test_default_options():
    """Test default values when no arguments are provided."""
    options = get_parser([])
    assert isinstance(options, Options)
    assert options.format is False
    assert options.dry_run is False
    assert options.version is False
    assert options.variables_file == "variables.tf"
    assert options.readme_file == "README.md"
    assert options.source is None
    assert options.git_source is False
    assert options.module_name is None


def test_custom_module_name():
    """Test setting custom module name."""
    options = get_parser(["--name", "custom-module"])
    assert options.module_name == "custom-module"

    options = get_parser(["-n", "custom-module"])
    assert options.module_name == "custom-module"


def test_custom_readme_file():
    """Test setting custom README file name."""
    options = get_parser(["--readme", "CUSTOM_README.md"])
    assert options.readme_file == "CUSTOM_README.md"


def test_custom_variables_file():
    """Test setting custom variables file name."""
    options = get_parser(["--variables", "custom_vars.tf"])
    assert options.variables_file == "custom_vars.tf"


def test_source_options():
    """Test source and git-source options."""
    # Test source without git-source
    options = get_parser(["--source", "github.com/user/repo"])
    assert options.source == "github.com/user/repo"
    assert options.git_source is False

    # Test source with git-source
    options = get_parser(["--source", "github.com/user/repo", "--git-source"])
    assert options.source == "github.com/user/repo"
    assert options.git_source is True


def test_format_flag():
    """Test format flag."""
    options = get_parser(["-f"])
    assert options.format is True


def test_dry_run_flag():
    """Test dry-run flag."""
    options = get_parser(["--dry-run"])
    assert options.dry_run is True


def test_version_flag():
    """Test version flag."""
    options = get_parser(["--version"])
    assert options.version is True


def test_get_version():
    """Test get_version returns a string."""
    version = get_version()
    assert isinstance(version, str) or version is None


def test_multiple_options():
    """Test combining multiple options."""
    options = get_parser([
        "--name", "custom-module",
        "--readme", "CUSTOM_README.md",
        "--variables", "custom_vars.tf",
        "--source", "github.com/user/repo",
        "--git-source",
        "-f",
        "--dry-run"
    ])
    
    assert options.module_name == "custom-module"
    assert options.readme_file == "CUSTOM_README.md"
    assert options.variables_file == "custom_vars.tf"
    assert options.source == "github.com/user/repo"
    assert options.git_source is True
    assert options.format is True
    assert options.dry_run is True 
