{
  description = "Factorio Bot";

  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        pythonPackages =
          ps:
          with ps;
          (
            [
              setuptools
              python-telegram-bot
              python-dotenv
              black
              httpx
              aiohttp
            ]
            ++ python-telegram-bot.optional-dependencies.job-queue
          );

        bot = pkgs.python3Packages.buildPythonApplication {
          pname = "functorio";
          version = "0.1.0";
          src = ./.;
          propagatedBuildInputs = (pythonPackages pkgs.python3.pkgs);
          nativeBuildInputs = [ pkgs.pkg-config ];
          PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
          pyproject = true;
          build-system = [ pkgs.python3Packages.setuptools ];
        };
      in
      {
        packages.default = bot;

        apps.default = {
          type = "app";
          program = "${bot}/bin/functorio";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            (pkgs.python3.withPackages pythonPackages)
            pkgs.flyctl
          ];
          nativeBuildInputs = [ pkgs.pkg-config ];
          PKG_CONFIG_PATH = "${pkgs.openssl.dev}/lib/pkgconfig";
        };
      }
    );
}