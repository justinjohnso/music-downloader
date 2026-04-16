# streamrip local overrides

This directory stores patch files for local modifications made inside the `vendor/streamrip` submodule.

Use the helper script from the project root:

```bash
./scripts/streamrip-overrides.sh status
./scripts/streamrip-overrides.sh export
./scripts/streamrip-overrides.sh check
./scripts/streamrip-overrides.sh apply
```

Current patch series:

- `0001-local-overrides.patch`: local streamrip behavior changes currently applied in this repo.
