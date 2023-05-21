import argparse
import os
import subprocess as sp
from pathlib import Path

args = argparse.ArgumentParser()
args.add_argument("-si", "--skip-install", action="store_true", help="Skip installing dependencies")
args.add_argument("-sv", "--skip-venv-enter", action="store_true", help="Skip Entering virtualenv")
parser = args.parse_args()

current_path = Path(__file__).absolute().parent.parent
print(f"[*] Running at {current_path}")

valid_venv_paths = [current_path / "venv", current_path / "env", current_path / ".venv"]

valid_venv: Path = None
for path in valid_venv_paths:
    if path.exists():
        valid_venv = path
        break


if valid_venv is None:
    print("[?] Creating venv since it's missing!")
    venv_exec = sp.Popen(["pip", "install", "virtualenv"], stdout=sp.DEVNULL, stderr=sp.DEVNULL).wait()
    venv_path = sp.Popen(["virtualenv", "venv"], stdout=sp.DEVNULL, stderr=sp.DEVNULL).wait()
    if venv_path != 0:
        raise Exception("Failed to create venv")
    valid_venv = current_path / "venv"
print(f"[*] Using venv at {valid_venv}")


if not parser.skip_venv_enter:
    if os.name == "nt":
        activate_script = valid_venv / "Scripts" / "activate.bat"
        sp.run(["cmd", "/C", str(activate_script)])
    else:
        activate_script = valid_venv / "bin" / "activate"
        sp.run(["source", str(activate_script)])

requirements_path = current_path / "requirements-dev.txt"
constraints_path = current_path / "constraints.txt"
if not parser.skip_install:
    print(f"[*] Installing requirements from {requirements_path}")
    sp.run(
        [
            "pip",
            "install",
            "-r",
            str(requirements_path),
            "-c",
            str(constraints_path),
        ],
        stdout=sp.DEVNULL,
        stderr=sp.DEVNULL,
    )


print("[*] Running tests")
print("[*] Running isort test...")
isort_res = sp.Popen(["isort", "-c", "nn"]).wait()
print("[*] Running flake8 test...")
flake8_res = sp.Popen(["flake8", "--statistics", "--show-source", "--benchmark", "--tee", "nn"]).wait()
print("[*] Running black test...")
black_res = sp.Popen(["black", "--check", "nn"]).wait()

results = [(isort_res, "isort"), (flake8_res, "flake8"), (black_res, "black")]
any_error = False

for res in results:
    if res[0] != 0:
        print(f"[-] {res[1]} returned an non-zero code")
        any_error = True
    else:
        print(f"[+] {res[1]} passed")

if any_error:
    print("[-] Test finished, but some tests failed")
    exit(1)
print("[+] All tests passed")
exit(0)