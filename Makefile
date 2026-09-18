.PHONY: public-release-stage public-release-check

PUBLIC_RELEASE_TARGET ?= build/public-release

public-release-stage:
	bash scripts/public_release_stage.sh "$(PUBLIC_RELEASE_TARGET)"

public-release-check:
	bash scripts/public_release_check.sh "$(PUBLIC_RELEASE_TARGET)"