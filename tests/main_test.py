import errno
from unittest.mock import patch, MagicMock

import pytest

from tfdocs.__main__ import main, report_and_exit, _cli_entrypoint


def test_main_version_flag(capsys):
    """Test main function with version flag."""
    with pytest.raises(SystemExit) as exc_info:
        main(["tfdocs", "--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "tfdocs" in captured.out


@patch("tfdocs.readme.Readme")
def test_main_dry_run_with_format(mock_readme):
    """Test main function with dry-run and format flags."""
    mock_instance = MagicMock()
    mock_instance.get_status.return_value = {"variables": True, "readme": False}
    mock_readme.return_value = mock_instance

    with pytest.raises(SystemExit) as exc_info:
        main(["tfdocs", "--dry-run", "-f"])
    assert exc_info.value.code == -1

    mock_instance.print_variables_file.assert_called_once()
    mock_instance.print_readme.assert_called_once()


@patch("tfdocs.readme.Readme")
def test_main_dry_run_with_format_and_no_variable_changes(mock_readme):
    """Test dry-run+format branch when variables.tf is already formatted."""
    mock_instance = MagicMock()
    mock_instance.get_status.return_value = {"variables": False, "readme": True}
    mock_readme.return_value = mock_instance

    with pytest.raises(SystemExit) as exc_info:
        main(["tfdocs", "--dry-run", "-f"])
    assert exc_info.value.code == -1

    mock_instance.print_variables_file.assert_called_once()
    mock_instance.print_readme.assert_called_once()


@patch("tfdocs.readme.Readme")
def test_main_dry_run_without_format(mock_readme):
    """Test main function with dry-run flag only."""
    mock_instance = MagicMock()
    mock_instance.get_status.return_value = {"variables": False, "readme": True}
    mock_readme.return_value = mock_instance

    with pytest.raises(SystemExit) as exc_info:
        main(["tfdocs", "--dry-run"])
    assert exc_info.value.code == -1

    mock_instance.print_variables_file.assert_not_called()
    mock_instance.print_readme.assert_called_once()


@patch("tfdocs.readme.Readme")
def test_main_format_only(mock_readme):
    """Test main function with format flag only."""
    mock_instance = MagicMock()
    mock_instance.get_status.return_value = {"variables": True, "readme": False}
    mock_readme.return_value = mock_instance

    with pytest.raises(SystemExit) as exc_info:
        main(["tfdocs", "-f"])
    assert exc_info.value.code == -1

    mock_instance.write_variables.assert_called_once()
    mock_instance.write_readme.assert_called_once()


@patch("tfdocs.readme.Readme")
def test_main_no_changes(mock_readme):
    """Test main function when no changes are needed."""
    mock_instance = MagicMock()
    mock_instance.get_status.return_value = {"variables": False, "readme": False}
    mock_readme.return_value = mock_instance

    with pytest.raises(SystemExit) as exc_info:
        main(["tfdocs"])
    assert exc_info.value.code == 0


def test_report_and_exit_with_changes(capsys):
    """Test report_and_exit with changes."""
    status = {"readme": True, "variables": True}
    with pytest.raises(SystemExit) as exc_info:
        report_and_exit(status, "README.md", "variables.tf", True, False)
    assert exc_info.value.code == -1

    captured = capsys.readouterr()
    assert "Updated:" in captured.out
    assert "README.md" in captured.out
    assert "variables.tf" in captured.out


def test_report_and_exit_no_changes(capsys):
    """Test report_and_exit without changes."""
    status = {"readme": False, "variables": False}
    with pytest.raises(SystemExit) as exc_info:
        report_and_exit(status, "README.md", "variables.tf", True, False)
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "Nothing to update!!!" in captured.out


@patch("tfdocs.__main__.main")
def test_cli_entrypoint_keyboard_interrupt(mock_main):
    """Test _cli_entrypoint with KeyboardInterrupt."""
    mock_main.side_effect = KeyboardInterrupt()

    with pytest.raises(SystemExit) as exc_info:
        _cli_entrypoint()
    assert exc_info.value.code == 130


@patch("tfdocs.__main__.main")
def test_cli_entrypoint_runtime_error(mock_main):
    """Test _cli_entrypoint with RuntimeError."""
    mock_main.side_effect = RuntimeError("Test error")

    with pytest.raises(SystemExit) as exc_info:
        _cli_entrypoint()
    assert str(exc_info.value) == "Test error"


@patch("tfdocs.__main__.main")
def test_cli_entrypoint_os_error(mock_main):
    """Test _cli_entrypoint with OSError."""
    mock_main.side_effect = OSError(errno.EPIPE, "Broken pipe")

    # Should not raise for EPIPE
    _cli_entrypoint()

    # Should raise for other OSErrors
    mock_main.side_effect = OSError(errno.EACCES, "Permission denied")
    with pytest.raises(OSError) as exc_info:
        _cli_entrypoint()
    assert exc_info.value.errno == errno.EACCES 
