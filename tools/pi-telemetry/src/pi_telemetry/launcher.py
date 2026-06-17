from __future__ import annotations

import json
import os
import sys

from pi_telemetry import __version__
from pi_telemetry import dashboard
from pi_telemetry.updater import (
    UPDATE_MODE_ENV,
    UPDATE_NOTICE_ENV,
    apply_update,
    build_update_notice,
    detect_install_root,
    normalize_update_mode,
)


def main() -> None:
    args = dashboard.parse_args()
    install_root = detect_install_root()
    update_mode = normalize_update_mode(os.environ.get(UPDATE_MODE_ENV))
    if update_mode == "off":
        os.environ.pop(UPDATE_NOTICE_ENV, None)
    else:
        update_notice = build_update_notice(__version__, install_root=install_root)
        os.environ[UPDATE_NOTICE_ENV] = json.dumps(update_notice)

        if (
            update_mode == "auto"
            and bool(update_notice.get("available"))
            and bool(update_notice.get("auto_update_ready", True))
        ):
            result = apply_update(update_notice, install_root=install_root)
            if result.get("ok"):
                os.execv(
                    sys.executable,
                    [sys.executable, "-m", "pi_telemetry.launcher", *sys.argv[1:]],
                )

    dashboard.main(args)


if __name__ == "__main__":
    main()
