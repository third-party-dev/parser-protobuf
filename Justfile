bundle DURATION="":
    ./scripts/create-bundle.sh {{DURATION}}

buildpkgs TAG="":
    ./scripts/build-pkgs.sh {{TAG}}

builddevpkgs TAG="":
    ./scripts/build-dev-pkgs.sh {{TAG}}

test:
    ./scripts/pytest.sh

format:
    @echo "--- ruff format ---"
    @ruff format .
    @echo "--- spacing methods ---"
    @./scripts/method_spacing.py

checks:
    @ruff check .
    #@mypy .