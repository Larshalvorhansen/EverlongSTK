{
  description = "EverlongSTK Python/PySide6 development environment";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { self, nixpkgs }:
    let
      # The development targets; broaden only after smoke-testing the new system.
      systems = [ "aarch64-darwin" "x86_64-linux" "aarch64-linux" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems
        (system: f nixpkgs.legacyPackages.${system});
    in
    {
      devShells = forAllSystems (pkgs:
        let
          python = pkgs.python313.withPackages (ps: with ps; [
            pyside6
            numpy
            matplotlib
            pyqtgraph
            pytest
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [
              python
              pkgs.ruff
              pkgs.git
            ];

            shellHook = ''
              # Editable source without pip installs or a second Python environment.
              export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
              echo "EverlongSTK dev shell: Python + PySide6 + pytest + Ruff"
              echo "Try: python -m everlong_stk --help"
            '';
          };
        });
    };
}
