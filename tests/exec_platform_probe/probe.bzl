TYPE = "@buildifier_prebuilt//buildifier:toolchain"

def _forward(ctx):
    return [DefaultInfo(files = depset([ctx.toolchains[TYPE]._tool]))]

native_forward = rule(implementation = _forward, toolchains = [TYPE])

def _probe(ctx):
    tool = ctx.file.tool if ctx.attr.tool else ctx.toolchains[TYPE].tool
    out = ctx.actions.declare_file(ctx.label.name + ".version")
    ctx.actions.run_shell(
        inputs = [tool],
        outputs = [out],
        arguments = [tool.path, out.path],
        command = '"$1" --version > "$2"',
        mnemonic = "GetBuildifierVersion",
        toolchain = None if ctx.attr.tool else TYPE,
    )
    return [DefaultInfo(files = depset([out]))]

probe = rule(
    implementation = _probe,
    attrs = {"tool": attr.label(allow_single_file = True, cfg = "exec")},
    toolchains = [TYPE],
)

def _native_check(ctx):
    output = ctx.actions.declare_directory(ctx.label.name + ".checked")
    ctx.actions.run(
        executable = ctx.toolchains[TYPE].tool,
        arguments = ["-mode=check", ctx.file.src.path],
        inputs = [ctx.file.src],
        outputs = [output],
        env = {"PATH": ""},
        mnemonic = "NativeBuildifierCheck",
        toolchain = TYPE,
    )
    return [DefaultInfo(files = depset([output]))]

native_check = rule(
    implementation = _native_check,
    attrs = {"src": attr.label(allow_single_file = [".bzl"])},
    toolchains = [TYPE],
)

def _legacy(ctx):
    # Reproduce the provider exposed to custom registrations before this PR.
    return [platform_common.ToolchainInfo(
        _tool = ctx.file.tool,
        _binary_runner = ctx.attr.wrapper,
        _runner = ctx.attr.scan,
    )]

legacy = rule(
    implementation = _legacy,
    attrs = {
        "scan": attr.label(default = "//:runner.bash.template", allow_single_file = True),
        "tool": attr.label(default = ":legacy.sh", allow_single_file = True),
        "wrapper": attr.label(default = "//:binary_runner.bash.template", allow_single_file = True),
    },
)
