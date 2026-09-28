import os, glob
base = "/home/frappe/frappe-bench/apps/custom_theme"
print("=== custom_theme .py files ===")
for p in glob.glob(base + "/**/*.py", recursive=True):
    print(p)
print("=== aig_setup modules present? (no import) ===")
for n in range(1, 9):
    p = f"{base}/custom_theme/aig_setup_0{n}.py"
    print(f"aig_setup_0{n}.py ->", os.path.exists(p))
print("CHECK_DONE")
