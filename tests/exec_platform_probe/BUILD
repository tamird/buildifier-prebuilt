load("//:toolchain.bzl", "prebuilt_toolchain")
load(":probe.bzl", "legacy", "native_check", "native_forward", "probe")

platform(
    name = "foreign",
    constraint_values = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
)

native_forward(name = "unconstrained")

[
    probe(
        name = name,
        tool = tool,
        exec_compatible_with = ["@platforms//os:linux"],
    )
    for name, tool in [
        ("unconstrained_dep", ":unconstrained"),
        ("direct", None),
    ]
]

native_check(name = "clean", src = "clean.bzl")

native_check(name = "bad", src = "bad.bzl")

legacy(name = "custom_provider")

toolchain(
    name = "legacy_toolchain",
    toolchain = ":custom_provider",
    toolchain_type = "//buildifier:toolchain",
)

prebuilt_toolchain(
    name = "custom_buildifier",
    binary_runner = "//:binary_runner.bash.template",
    runner = "//:runner.bash.template",
    tool = ":legacy.sh",
)

toolchain(
    name = "custom_toolchain",
    toolchain = ":custom_buildifier",
    toolchain_type = "//buildifier:toolchain",
)
