import sys
import os
import subprocess
import time

def run_script(script_name):
    print(f"\n[{script_name}] Running...")
    start = time.time()
    # verify_p3 requires P3 feature flag? No, verify_p3.py enables it in the request.
    # verify_p3 check is: default OFF, passed if explicitly ON.
    # The script tests verify_p3.py handles the ON case (it enables it in req).
    
    # We should also verified default is OFF? 
    # verify_p0.py does standard requests (GlobalSettings default).
    # If verify_p0 passes, P3 is effectively not breaking basic logic.
    
    cmd = [sys.executable, script_name]
    try:
        # Capture output mixed with stdout
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__), capture_output=True, text=True)
        duration = time.time() - start
        
        # Write log
        # If running from solver-py/ (CWD), and we want solver-py/artifacts/verification
        # We should just use "artifacts/verification"
        log_name = f"artifacts/verification/{os.path.basename(script_name).replace('.py', '.log')}"
        os.makedirs(os.path.dirname(log_name), exist_ok=True)
        with open(log_name, "w") as f:
            f.write(result.stdout)
            f.write("\n=== STDERR ===\n")
            f.write(result.stderr)
            
        print(f"[{script_name}] Finished in {duration:.2f}s. Exit Code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"FAIL: {script_name} failed. See {log_name}")
            print("Last 10 lines of output:")
            print("\n".join(result.stdout.splitlines()[-10:]))
            return False
            
        print(f"PASS: {script_name}")
        return True
        
    except Exception as e:
        print(f"CRITICAL: Error running {script_name}: {e}")
        return False

def main():
    print("=== Verification Harness: Phase 0 Release Candidate ===")
    
    # Ensure artifacts dir
    os.makedirs("../artifacts/verification", exist_ok=True)
    
    scripts = [
        "verify_p0.py",
        "verify_p1_p2.py",
        "verify_p3.py",
        "certify_phase0.py"
    ]
    
    results = {}
    all_pass = True
    
    for s in scripts:
        passed = run_script(s)
        results[s] = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
            # Strict exit? User said "run in order, with strict exit codes". 
            # Usually implies stop on fail.
            print("Stopping due to failure.")
            break
            
    print("\n=== Summary ===")
    for s, status in results.items():
        print(f"{s}: {status}")
        
    if all_pass:
        print("\nALL TESTS PASSED. READY FOR RELEASE.")
        sys.exit(0)
    else:
        print("\nVERIFICATION FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
