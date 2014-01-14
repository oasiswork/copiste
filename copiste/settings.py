import importlib
import os
import sys

if os.environ.has_key('COPISTE_SETTINGS_MODULE'):
    COPISTE_SETTINGS_MODULE = os.environ['COPISTE_SETTINGS_MODULE']
else:
    COPISTE_SETTINGS_MODULE = 'settings'

SETTINGS = importlib.import_module(COPISTE_SETTINGS_MODULE)

