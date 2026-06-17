from __future__ import annotations

import json
import os

from pi_telemetry import __version__
from pi_telemetry import dashboard
from pi_telemetry.updater import UPDATE_NOTICE_ENV, build_update_notice, detect_install_root


def main() -> None:
    args = dashboard.parse_args()
    install_root = detect_install_root()
    update_notice = build_update_notice(__version__, install_root=install_root)
    os.environ[UPDATE_NOTICE_ENV] = json.dumps(update_notice)

    dashboard.main(args)


if __name__ == "__main__":
    main()
