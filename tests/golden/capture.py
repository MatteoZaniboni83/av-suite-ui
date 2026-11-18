"""Recapture an app's golden stylesheets, run with that app's own venv.

    cd ../media-transfer && PYTHONPATH=src .venv/bin/python \
        "../av-suite ui/tests/golden/capture.py" media_transfer MEDIA_TRANSFER_DATA_DIR

Writes <package>_dark.qss and <package>_light.qss beside this file: the app's
build_stylesheet(mode) with the default accent, its data dir pointed at a
throwaway folder and that folder's icons path written as @ICON_DIR@.
"""

import importlib
import os
import sys
import tempfile

package, env_var = sys.argv[1:3]
data = tempfile.mkdtemp(prefix="golden-")
os.environ[env_var] = data
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
theme = importlib.import_module(package + ".ui.theme")
icons = os.path.join(data, "icons").replace("\\", "/")
here = os.path.dirname(os.path.abspath(__file__))
for mode in ("dark", "light"):
    qss = theme.build_stylesheet(mode)
    assert icons in qss, "the icons did not go to the throwaway data dir"
    with open(os.path.join(here, f"{package}_{mode}.qss"), "w", encoding="utf-8") as f:
        f.write(qss.replace(icons, "@ICON_DIR@"))
    print("wrote", f"{package}_{mode}.qss")
