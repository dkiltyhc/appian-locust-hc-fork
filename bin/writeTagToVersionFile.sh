#!/bin/bash

CURRENT_DIR=$(dirname "$0")
version_file=$CURRENT_DIR/../appian_locust/VERSION

branch_sha="$CI_COMMIT_SHORT_SHA"
version_to_use=${CI_COMMIT_TAG:-"$branch_sha"}

if [[ -z "$version_to_use" ]]; then
    printf "%s" "UNKNOWN" > "$version_file"
else
    printf "%s" "$version_to_use" > "$version_file"
fi
