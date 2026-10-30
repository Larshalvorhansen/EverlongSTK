"""Bootstrap checks deliberately do not import Qt or require a display."""

from everlong_stk.cli import create_parser, main


def test_help_is_accessible_without_qt(capsys) -> None:
    assert main([]) == 0
    assert "gui" in capsys.readouterr().out


def test_gui_command_parses() -> None:
    assert create_parser().parse_args(["gui"]).command == "gui"


def test_environment_command_parses() -> None:
    assert create_parser().parse_args(["check-env"]).command == "check-env"
