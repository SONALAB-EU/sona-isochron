#!/bin/bash
# On the Mac: copy track_2b/ to the cluster (the allowlist in hpc/sync_include.txt) and record there, in
# isochron/track_2b/.git_commit, which commit the copy is. The copy is not a git checkout, so that file is
# what every results file made on the cluster reports as its commit (isochron.provenance).
#
#   bash hpc/sync.sh HOST          for example: bash hpc/sync.sh hpi-login
#
# Uncommitted changes to tracked files, and new files under src/, hpc/, data/ or tests/, are recorded as
# "with uncommitted changes". Nothing on the cluster is deleted.
set -euo pipefail

main() {
    local host=${1:?usage: bash hpc/sync.sh HOST} commit changes
    cd "$(dirname "${BASH_SOURCE[0]}")/.."
    commit=$(git rev-parse HEAD)
    changes=$(git status --porcelain --untracked-files=no; git status --porcelain --untracked-files=all -- src hpc data tests | grep '^??' || true)
    [ -z "$changes" ] || commit="$commit (with uncommitted changes)"
    ssh "$host" mkdir -p isochron/track_2b
    rsync -av --filter='merge hpc/sync_include.txt' ./ "$host:isochron/track_2b/"
    printf '%s\n' "$commit" | ssh "$host" 'cat > isochron/track_2b/.git_commit'
    echo "the copy on $host is $commit"
}

# bash reads a script while it runs it; with everything in main and this one last line, the file is read to
# the end before anything runs
main "$@"; exit
