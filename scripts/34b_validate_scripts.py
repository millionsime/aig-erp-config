# AIG config - step 34b: compile-check every AIG inventory Server Script under
# RestrictedPython so runtime surprises are caught now, not during the demo.
import frappe

compile_restricted = None
try:
    import inspect
    from frappe.utils import safe_exec
    from frappe.utils.safe_exec import compile_restricted
    print("signature:", inspect.signature(compile_restricted))
    print("policy-ish:", [n for n in dir(safe_exec) if "olic" in n])
except Exception as e:
    print("compile_restricted import failed:", e)

names = [
    "AIG - MR Request Defaults",
    "AIG - MR Approval Guard",
    "AIG - SE Movement Defaults",
    "AIG - SE Receiving Inspection Gate",
    "AIG - SE Guard Raw Submit",
    "AIG - SE Issue Validation",
    "AIG - Item Duplicate Name Warning",
]

ok = 0
bad = 0
for n in names:
    if not frappe.db.exists("Server Script", n):
        print(f"MISSING: {n}")
        bad += 1
        continue
    script = frappe.db.get_value("Server Script", n, "script")
    if compile_restricted is None:
        print(f"SKIP (no compiler): {n}")
        continue
    try:
        compile_restricted(script, filename=n)
        print(f"OK   : {n}")
        ok += 1
    except TypeError:
        try:
            compile_restricted(script)
            print(f"OK   : {n}")
            ok += 1
        except Exception as e2:
            print(f"ERROR: {n} -> {type(e2).__name__}: {e2}")
            bad += 1
    except Exception as e:
        print(f"ERROR: {n} -> {type(e).__name__}: {e}")
        bad += 1

print(f"\nCOMPILE_CHECK ok={ok} bad={bad}")
