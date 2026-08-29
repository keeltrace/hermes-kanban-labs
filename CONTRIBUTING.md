# Contributing

This project is for Hermes power users who want to prove advanced Kanban execution patterns before every upstream interface is finalized.

## Contribution rule

A contribution should either:

- make an existing upstream primitive usable in a new worker environment;
- improve failure/recovery evidence;
- add a backend without creating another Kanban authority;
- improve compatibility with current Hermes `main`;
- remove Labs code because upstream now provides the capability natively.

Please do not add a second task scheduler, board database, dependency engine, retry ledger, or orchestration framework.

## Before opening a PR

```bash
./scripts/smoke.sh
```

Also run against a current Hermes checkout when your change touches integration behavior:

```bash
python scripts/apply_upstream_patch.py /path/to/hermes-agent
python scripts/verify_upstream_contract.py /path/to/hermes-agent
```

For hardware-specific changes, include the actual environment tested: OS, architecture, Docker version, Hermes upstream SHA, model backend, network shape, and failure cases exercised.
