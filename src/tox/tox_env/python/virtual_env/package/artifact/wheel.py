from pathlib import Path
from typing import Any, Tuple

from packaging.requirements import Requirement

from tox.plugin.impl import impl
from tox.tox_env.register import ToxEnvRegister

from ..api import Pep517VirtualEnvPackage


class Pep517VirtualEnvPackageWheel(Pep517VirtualEnvPackage):
    @staticmethod
    def id() -> str:
        return "virtualenv-pep-517-wheel"

    def build_requires(self) -> Tuple[Requirement, ...]:
        result = self.get_requires_for_build_wheel()
        return result.requires

    def _build_artifact(self) -> Path:
        result = self.build_wheel(
            wheel_directory=self.pkg_dir,
            metadata_directory=self.meta_folder,
            config_settings={"--global-option": ["--bdist-dir", str(self.conf["env_dir"] / "build")]},
        )
        return result.wheel

    def _send(self, cmd: str, missing: Any, **kwargs: Any) -> Tuple[Any, str, str]:
        if cmd == "prepare_metadata_for_build_wheel":
            # given we'll build a wheel we might skip the prepare step
            return None, "", ""
        return super()._send(cmd, missing, **kwargs)


@impl
def tox_register_tox_env(register: ToxEnvRegister) -> None:
    register.add_package_env(Pep517VirtualEnvPackageWheel)
