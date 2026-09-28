import frappe


def run(path):
    """Execute a standalone AIG setup script inside a proper bench context.

    Runs the file in a fresh namespace (frappe pre-injected) so module-level
    variables stay consistent, then commits. Invoked via:
        bench --site frontend execute custom_theme.aig_runner.run --kwargs "{'path': '/tmp/xx.py'}"
    """
    with open(path) as f:
        code = f.read()
    ns = {"frappe": frappe, "__name__": "__aig_script__", "__file__": path}
    exec(compile(code, path, "exec"), ns)
    frappe.db.commit()
    return f"OK:{path}"
