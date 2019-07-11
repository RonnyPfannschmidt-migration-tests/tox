import argparse
import logging
from argparse import SUPPRESS, Action, ArgumentDefaultsHelpFormatter, ArgumentParser, Namespace
from itertools import chain
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type, TypeVar, cast

from tox.plugin.util import NAME
from tox.session.state import State

from .env_var import get_env_var
from .ini import IniConfig


class ArgumentParserWithEnvAndConfig(ArgumentParser):
    """
    Custom option parser which updates its defaults by checking the configuration files and environmental variables
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.file_config = IniConfig()
        kwargs["epilog"] = self.file_config.epilog
        super(ArgumentParserWithEnvAndConfig, self).__init__(*args, **kwargs)

    def fix_defaults(self) -> None:
        for action in self._actions:
            self.fix_default(action)

    def fix_default(self, action: Action) -> None:
        if hasattr(action, "default") and hasattr(action, "dest") and action.default != SUPPRESS:
            of_type = self.get_type(action)
            key = action.dest
            outcome = get_env_var(key, of_type=of_type)
            if outcome is None and self.file_config:
                outcome = self.file_config.get(key, of_type=of_type)
            if outcome is not None:
                action.default, action.default_source = outcome
        if isinstance(action, argparse._SubParsersAction):
            for values in action.choices.values():
                values.fix_defaults()

    @staticmethod
    def get_type(action):
        of_type = getattr(action, "of_type", None)
        if of_type is None:
            if action.default is not None:
                of_type = type(action.default)
            elif isinstance(action, argparse._StoreConstAction) and action.const is not None:
                of_type = type(action.const)
            else:  # pragma: no cover
                raise TypeError(action)  # pragma: no cover
        return of_type


class HelpFormatter(ArgumentDefaultsHelpFormatter):
    def __init__(self, prog: str) -> None:
        super(HelpFormatter, self).__init__(prog, max_help_position=42, width=240)

    def _get_help_string(self, action: Action) -> str:
        text = super()._get_help_string(action)
        if hasattr(action, "default_source"):
            default = " (default: %(default)s)"
            if text.endswith(default):
                text = "{} (default: %(default)s -> from %(default_source)s)".format(
                    text[: -len(default)]
                )
        return text


class Parsed(Namespace):
    @property
    def verbosity(self) -> int:
        return max(self.verbose - self.quiet, 0)


Handler = Callable[[State], Optional[int]]


ToxParserT = TypeVar("ToxParserT", bound="ToxParser")


class ToxParser(ArgumentParserWithEnvAndConfig):
    def __init__(
        self, *args: Any, root: bool = False, add_cmd: bool = False, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if root is True:
            self._add_base_options()
        self.handlers: Dict[str, Tuple[Any, Handler]] = {}
        if add_cmd is True:
            self._cmd = self.add_subparsers(
                title="command", help="tox command to execute", dest="command", required=False
            )
            self._cmd.default = "run"

        else:
            self._cmd = None

    def add_command(self, cmd: str, aliases: Sequence[str], help_msg: str, handler: Handler):
        sub_parser = self._cmd.add_parser(
            cmd, help=help_msg, aliases=aliases, formatter_class=HelpFormatter
        )
        content = sub_parser, handler
        self.handlers[cmd] = content
        for alias in aliases:
            self.handlers[alias] = content
        return sub_parser

    def add_argument(self, *args, of_type=None, **kwargs) -> Action:
        result = super().add_argument(*args, **kwargs)
        if of_type is not None:
            result.of_type = of_type
        return result

    @classmethod
    def base(cls: Type[ToxParserT]) -> ToxParserT:
        return cls(add_help=False, root=True)

    @classmethod
    def core(cls: Type[ToxParserT]) -> ToxParserT:
        return cls(prog=NAME, formatter_class=HelpFormatter, add_cmd=True, root=True)

    def _add_base_options(self) -> None:
        from tox.report import LEVELS

        level_map = "|".join(
            "{} - {}".format(c, logging.getLevelName(l)) for c, l in sorted(list(LEVELS.items()))
        )
        verbosity_group = self.add_argument_group(
            "verbosity=verbose-quiet, default {}, map {}".format(
                logging.getLevelName(LEVELS[3]), level_map
            )
        )
        verbosity_exclusive = verbosity_group.add_mutually_exclusive_group()
        verbosity_exclusive.add_argument(
            "-v", "--verbose", action="count", dest="verbose", help="increase verbosity", default=2
        )
        verbosity_exclusive.add_argument(
            "-q", "--quiet", action="count", dest="quiet", help="decrease verbosity", default=0
        )
        self.fix_defaults()

    def parse(self, args: Sequence[str]) -> Tuple[Parsed, List[str]]:
        arg_set = set(args)
        if (
            "-h" not in arg_set
            and "--help" not in arg_set
            and self._cmd is not None
            and not (arg_set & set(self.handlers.keys()))
        ):
            global_args = set(
                chain.from_iterable(
                    i.option_strings for i in self._actions if hasattr(i, "option_strings")
                )
            )
            first_differ = next((i for i, j in enumerate(args) if j not in global_args), 0)
            new_args = list(args[:first_differ])
            new_args.append(self._cmd.default or "run")
            new_args.extend(args[first_differ:])
            args = new_args
        parsed, unknown = super().parse_known_args(args, namespace=Parsed())
        return cast(Parsed, parsed), unknown
