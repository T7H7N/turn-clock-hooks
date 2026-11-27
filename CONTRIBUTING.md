# Contributing

Keep each hook usable by itself with Python 3.9 or later and the standard library. For a behavior change, add one case for the event that should trigger it and one case for a similar input that should pass unchanged. Include a boundary case when paths, encodings, clocks, or thresholds matter.

Run the changed folder's `test_hook.py` and the collection's `install_check.py`. Keep the collection and folder registration examples in agreement. Use fictional paths and public inputs for tests.
