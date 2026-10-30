{
  description = "EverlongSTK development environment (schema milestone)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forSystems = f: builtins.listToAttrs (map (system: {
        name = system;
        value = f system;
      }) systems);
    in
    {
      devShells = forSystems (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python312
              python312Packages.pytest
              ruff
            ];
            shellHook = ''
              export PYTHONPATH="$PWD/src:$PYTHONPATH"
            '';
          };
        });
    };
}
