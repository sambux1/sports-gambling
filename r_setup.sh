#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export R_LIBS_USER="$PROJECT_DIR/.Rlib"
mkdir -p "$R_LIBS_USER"
Rscript - <<'R'
repos <- "https://cloud.r-project.org"
pkgs <- c("remotes","arrow")
need <- setdiff(pkgs, rownames(installed.packages()))
if (length(need)) install.packages(need, repos=repos)
if (!requireNamespace("nflreadr", quietly=TRUE)) remotes::install_github("nflverse/nflreadr")
R
