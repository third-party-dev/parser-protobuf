bundle DURATION="":
    ./scripts/create-bundle.sh {{DURATION}}

buildpkgs TAG="":
    ./scripts/build-pkgs.sh {{TAG}}

builddevpkgs TAG="":
    ./scripts/build-dev-pkgs.sh {{TAG}}

test:
    ./scripts/pytest.sh

checks:
    @ruff check .