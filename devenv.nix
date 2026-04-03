{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = [
    pkgs.git
    pkgs.uv
    (inputs.kiln.packages.${pkgs.system}.default.overrideAttrs (_: {
      # v0.9.5 flake ships a stale go modules hash; override to keep release pin usable.
      vendorHash = "sha256-HL4H+HOVHu7H71V7t4bjWBcquaimuh/GkPnuwPiuZ0A=";
      doCheck = false;
    }))
  ];

  # https://devenv.sh/languages/
  # languages.rust.enable = true;
  languages = {
      python = {
          enable = true;
          version = "3.13";
          venv.enable = true;
          uv.enable = true;
        };
    };

  # https://devenv.sh/processes/
  # processes.cargo-watch.exec = "cargo-watch";

  # https://devenv.sh/services/
  # services.postgres.enable = true;

  # https://devenv.sh/scripts/
  scripts.hello.exec = ''
    echo hello from $GREET
  '';
  scripts."bullish-ssg-validate".exec = "bullish-ssg validate";

  enterShell = ''
    hello
    git --version
  '';

  # https://devenv.sh/tasks/
  tasks = {
    "bullish-ssg:validate".exec = "bullish-ssg validate";
  };

  # https://devenv.sh/tests/
  enterTest = ''
    echo "Running tests"
    git --version | grep --color=auto "${pkgs.git.version}"
  '';

  # https://devenv.sh/pre-commit-hooks/
  # pre-commit.hooks.shellcheck.enable = true;

  # See full reference at https://devenv.sh/reference/options/
}
