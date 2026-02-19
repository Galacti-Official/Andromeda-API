import os
import importlib

package_dir = os.path.dirname(__file__)

for file in os.listdir(package_dir):
    if file.endswith(".py") and file != "__init__.py":
        importlib.import_module(f"{__name__}.{file[:-3]}")
