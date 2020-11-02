#!/usr/bin/env bash
# Stolen from https://stackoverflow.com/questions/40865597/generate-changelog-from-commit-and-tag
# Run with ./bin/generate_changelog.sh > appian_locust/docs/source/changelog.rst
previous_tag=0
echo "##################################"
echo "Changelog"
echo "##################################"
for current_tag in $(git tag --sort=-creatordate); do
    if [ "$previous_tag" != 0 ]; then
        tag_date=$(git log -1 --pretty=format:'%ad' --date=short ${previous_tag})
        printf "${previous_tag} (${tag_date})\n==================================\n"
        git log ${current_tag}...${previous_tag} --pretty=format:'*  %s (`View <https://gitlab.com/appian-oss/appian-locust/commit/%H>`__)' --reverse | grep -v Merge
        printf "\n\n"
    fi
    previous_tag=${current_tag}
done
