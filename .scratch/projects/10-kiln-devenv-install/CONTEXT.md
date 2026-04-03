# Context

- Task: ensure Kiln is installed through devenv.sh configuration so it is available in `devenv shell`.
- Verified repo currently uses `devenv.yaml` and `devenv.nix`; no separate `devenv.sh` script file exists.
- Current `devenv` packages: `git`, `uv`.
- Updated `devenv.yaml` Kiln input to pinned release `github:otaleghani/kiln/v0.9.5`.
- Updated `devenv.nix` packages with `inputs.kiln.packages.${pkgs.system}.default` and overrides:
  - `vendorHash = "sha256-HL4H+HOVHu7H71V7t4bjWBcquaimuh/GkPnuwPiuZ0A="` (fixes stale upstream hash in release flake).
  - `doCheck = false` (upstream Nix check phase fails for `v0.9.5` in builder context).
- Validation:
  - `devenv shell -- kiln --version` failed because this CLI uses subcommand style version output.
  - `devenv shell -- kiln version` succeeded and printed `kiln dev`.
