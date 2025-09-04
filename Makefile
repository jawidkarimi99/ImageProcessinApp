.PHONY: test perf profile resources load app

app:
\tpython src/gui.py

test:
\tpytest tests/unit

perf:
\tpytest tests/perf -m perf --benchmark-min-rounds=1 --benchmark-sort=mean --benchmark-json perf_results.json

profile:
\tpython scripts/profile_cprofile.py

resources:
\tpython scripts/measure_resources.py
\tpython scripts/plot_metrics.py

load:
\tpython scripts/stress_load.py
\tpython scripts/plot_load_curve.py
