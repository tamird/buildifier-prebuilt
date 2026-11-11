"""Exercise Buildifier's native action tool and CLI with two registered workers."""

import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

FIXED = "b2af4549b322845abb376b8186de340f0073bff5"
PUBLISHED = "0d4bbc198943e150cd0f1c8f27140d498aba67f3"
probe = Path(__file__).resolve().parent
src = Path("tests/exec_platform_probe")
out = Path(os.environ["RUNNER_TEMP"]) / "buildifier-results"
out.mkdir(exist_ok=True)
target = "//tests/exec_platform_probe:"
args = ["--lockfile_mode=off", "--repo_env=BAZEL_USE_CPP_ONLY_TOOLCHAIN=1"]
native = "linux_amd64" if platform.system() == "Linux" else "darwin_arm64"
foreign = "darwin_arm64" if platform.system() == "Linux" else "linux_amd64"
assets = {
    "linux_amd64": "31b6a8aa1e5c746696788f428729701770ad91925873d8256cb885c60e12c77e",
    "darwin_arm64": "e9804864c407f920f5ecbf03a5e056a8145e11a6ae6b90d2438a3fd106d34473",
}

def run(name, cmd, failure=False, cwd=None):
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (out / (name + ".txt")).write_text(proc.stdout)
    if (proc.returncode != 0) != failure:
        raise RuntimeError(f"{name}: {proc.returncode}\n{proc.stdout}")
    return proc.stdout

for version in ("7.6.1", "8.5.1", "9.3.1"):
    os.environ["USE_BAZEL_VERSION"] = version
    bazel = ["bazelisk", "--ignore_all_rc_files"]
    for stage, commit in (("published", PUBLISHED), ("fixed", FIXED)):
        name = f"{version}-{stage}"
        subprocess.run(["git", "switch", "--detach", commit], check=True)
        shutil.copytree(probe, src, ignore=shutil.ignore_patterns("qualify.py"))
        try:
            if foreign == "darwin_arm64":
                p = src / "BUILD"
                p.write_text(p.read_text().replace("@platforms//os:linux", "@platforms//os:macos")
                             .replace("@platforms//cpu:x86_64", "@platforms//cpu:arm64"))
            expected = {"direct": foreign, "unconstrained_dep": native}
            query = 'mnemonic("SelectBuildifier", set(' + " ".join(target + label for label in expected) + "))"
            aq = run(name + "-aquery", bazel + ["aquery", *args, "--extra_execution_platforms=@platforms//host:host,//tests/exec_platform_probe:foreign", "--output=text", query])
            base = Path(run(name + "-base", bazel + ["info", *args, "output_base"]).splitlines()[-1])
            for rule, cpu in expected.items():
                section = next(s for s in aq.split("\naction '") if f"Target: {target}{rule}\n" in s)
                assert f"Execution platform: {target}foreign\n" in section, section
                path = re.search(r"  Inputs: \[(external/[^\]]+)\]", section)[1]
                assert "buildifier_" + cpu + "/file/buildifier" in path, path
                data = (base/path).read_bytes()
                if cpu == "linux_amd64":
                    assert data[:4] == b"\x7fELF" and int.from_bytes(data[18:20], "little") == 62
                else:
                    assert data[:4] == bytes.fromhex("cffaedfe")
                assert hashlib.sha256(data).hexdigest() == assets[cpu], (path, cpu)
                print(name, rule, "requested", foreign, "selected", cpu, hashlib.sha256(data).hexdigest(), flush=True)
            if stage == "fixed":
                run(name+"-clean", bazel+["build", *args, target+"clean"])
                bad = run(name+"-bad", bazel+["build", *args, target+"bad"], failure=True)
                assert "bad.bzl # reformat" in bad, bad
                run(name+"-cli-test", bazel+["test", *args, "--test_output=errors", "//tests/binary_runner:binary_runner_test"])
                run(name+"-native-example", bazel+["test", *args, "--test_output=errors", "--nocache_test_results",
                    "--test_env=PATH=/usr/bin:/bin", "//..."], cwd="examples/bzlmod")
            custom = run(name+"-custom", bazel+["run", *args, "--extra_toolchains="+target+"custom_toolchain", "//:buildifier", "--", "-version"])
            assert "legacy-buildifier -version" in custom, custom
            legacy = run(name+"-handwritten", bazel+["run", *args, "--extra_toolchains="+target+"legacy_toolchain", "//:buildifier", "--", "-version"], failure=(stage == "fixed"))
            if stage == "fixed":
                assert "field" in legacy and "'tool'" in legacy, legacy
            else:
                assert "legacy-buildifier -version" in legacy, legacy
        finally:
            shutil.rmtree(src)
