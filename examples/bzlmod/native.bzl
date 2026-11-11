"""Run the native Buildifier executable as a Bazel test."""

_BUILDIFIER = "@buildifier_prebuilt//buildifier:toolchain"

def _native_buildifier_test_impl(ctx):
    tool = ctx.exec_groups["test"].toolchains[_BUILDIFIER].tool
    executable = ctx.actions.declare_file(ctx.label.name + "/" + tool.basename)
    ctx.actions.symlink(output = executable, target_file = tool, is_executable = True)
    return [DefaultInfo(executable = executable, runfiles = ctx.runfiles(files = ctx.files.srcs))]

native_buildifier_test = rule(
    implementation = _native_buildifier_test_impl,
    attrs = {"srcs": attr.label_list(allow_files = True)},
    exec_groups = {"test": exec_group(toolchains = [_BUILDIFIER])},
    test = True,
)
