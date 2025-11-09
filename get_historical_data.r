# Script to download historical player stats from the NFL using the existing R environment.
# If a project-local library exists, prefer it (no installs here).
local_lib <- file.path(getwd(), ".Rlib")
if (dir.exists(local_lib)) {
  .libPaths(c(local_lib, .libPaths()))
}

if (!requireNamespace("nflreadr", quietly = TRUE) || !requireNamespace("arrow", quietly = TRUE)) {
  stop("Required packages not installed. Run r_setup.sh first.", call. = FALSE)
}

library(nflreadr)
library(arrow)

# define seasons to download
seasons <- 2010:2024

# download player stats (one row per player per game)
player_stats <- load_player_stats(seasons)

# save to Parquet (compact, best for Python use)
write_parquet(player_stats, "player_stats_2010_2024.parquet")

cat("Done!\nSaved to: player_stats_2010_2024.parquet\n")
