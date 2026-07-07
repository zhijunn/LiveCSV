# -*- coding: utf-8 -*-
"""LiveCSV backend package — Flask app, storage, CSV I/O, and OS integration.

The launcher (:mod:`livecsv`, at the project root) imports the Flask ``app``
and helpers from here.  Path constants inside these modules resolve to the
project root (the parent of this package), so ``frontend/``, ``static/``,
``samples/``, ``uploads/``, ``logs/`` and ``state.json`` all stay where the
launcher and the front-end expect them.
"""
