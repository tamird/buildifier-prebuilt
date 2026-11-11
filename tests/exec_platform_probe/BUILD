load(":probe.bzl", "legacy", "native_check", "native_forward", "probe")

platform(
    name = "linux",
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
        ("published", "//buildifier:cli_binary"),
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
