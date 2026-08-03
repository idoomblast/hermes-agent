from agent.lsp.servers import ServerContext, _resolve_override, _spawn_pyright


def test_path_resolvable_override_keeps_custom_pyright_arguments(monkeypatch, tmp_path):
    monkeypatch.setattr("agent.lsp.servers.shutil.which", lambda command: "/usr/bin/ty" if command == "ty" else None)

    ctx = ServerContext(
        workspace_root=str(tmp_path),
        install_strategy="off",
        binary_overrides={"pyright": ["ty", "server"]},
    )

    assert _resolve_override(ctx, "pyright") == "/usr/bin/ty"
    spec = _spawn_pyright(str(tmp_path), ctx)

    assert spec is not None
    assert spec.command == ["/usr/bin/ty", "server"]
