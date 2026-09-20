.PHONY: public-release-stage public-release-check refresh-seed

PUBLIC_RELEASE_TARGET ?= build/public-release

public-release-stage:
	bash scripts/public_release_stage.sh "$(PUBLIC_RELEASE_TARGET)"

public-release-check:
	bash scripts/public_release_check.sh "$(PUBLIC_RELEASE_TARGET)"

# Refresh the bundled corpora/ seed from what the live site is serving.
# Stages the result; never commits. Needs SUBDOCENT_BASE_URL, ADMIN_USERNAME
# and ADMIN_PASSWORD in the environment.
refresh-seed:
	python3 scripts/refresh_seed.py $(ARGS)
