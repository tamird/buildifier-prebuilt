"""Exercise Buildifier's native action tool and CLI with two registered workers."""

import hashlib
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

FIXED = "dada54c5ba3baff3da348d1c8d952225448fa8d1"
PUBLISHED = "5357c442f1646fbcab29f3b63525fb280f4fc2ce"
probe = Path(__file__).resolve().parent
src = Path("tests/exec_platform_probe")
out = Path(os.environ["RUNNER_TEMP"]) / "buildifier-results"
out.mkdir(exist_ok=True)
target = "//tests/exec_platform_probe:"
query = 'mnemonic("GetBuildifierVersion", set(' + " ".join(target + label for label in ("published", "unconstrained_dep", "direct")) + "))"
args = ["--lockfile_mode=off", "--repo_env=BAZEL_USE_CPP_ONLY_TOOLCHAIN=1"]
mac = "darwin_arm64" if platform.machine() == "arm64" else "darwin_amd64"

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
            if stage == "published":
                p = src / "BUILD"
                p.write_text(p.read_text().replace("//buildifier:cli_binary", "//buildifier:native"))
                p = src / "probe.bzl"
                p.write_text(p.read_text().replace("ctx.toolchains[TYPE].tool", "ctx.toolchains[TYPE]._tool"))
            aq = run(name + "-aquery", bazel + ["aquery", *args, "--extra_execution_platforms=@platforms//host:host,//tests/exec_platform_probe:linux", "--output=text", query])
            base = Path(run(name + "-base", bazel + ["info", *args, "output_base"]).splitlines()[-1])
            expected = {"direct":"linux_amd64", "published":"linux_amd64" if version == "9.3.1" else mac, "unconstrained_dep":mac}
            for rule, cpu in expected.items():
                section = next(s for s in aq.split("\naction '") if f"Target: {target}{rule}\n" in s)
                assert f"Execution platform: {target}linux\n" in section, section
                path = re.search(r"  Inputs: \[(external/[^\]]+)\]", section)[1]
                assert "buildifier_" + cpu + "/file/buildifier" in path, path
                data = (base/path).read_bytes()
                if cpu == "linux_amd64":
                    assert data[:4] == b"\x7fELF" and int.from_bytes(data[18:20], "little") == 62
                    assert hashlib.sha256(data).hexdigest() == "31b6a8aa1e5c746696788f428729701770ad91925873d8256cb885c60e12c77e"
                else:
                    assert data[:4] == bytes.fromhex("cffaedfe")
                print(name, rule, "requested linux_amd64", "selected", cpu, hashlib.sha256(data).hexdigest(), flush=True)
            if stage == "fixed":
                run(name+"-clean", bazel+["build", *args, target+"clean"])
                bad = run(name+"-bad", bazel+["build", *args, target+"bad"], failure=True)
                assert "bad.bzl # reformat" in bad, bad
                run(name+"-cli-test", bazel+["test", *args, "--test_output=errors", "//tests/binary_runner:binary_runner_test"])
                legacy = run(name+"-legacy", bazel+["run", *args, "--extra_toolchains="+target+"legacy_toolchain", "//:buildifier", "--", "-version"])
                assert "legacy-buildifier -version" in legacy, legacy
        finally:
            shutil.rmtree(src)
