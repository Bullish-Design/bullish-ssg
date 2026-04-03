# Assumptions

- Request scope is limited to making `kiln` available inside this repo's `devenv` shell.
- "Installed via devenv.sh" means provisioned through Nix/devenv config (`devenv.yaml` + `devenv.nix`), not manual curl/go install.
- Existing in-flight repo changes are unrelated and must not be reverted.
