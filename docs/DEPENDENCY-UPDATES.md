# Dependency updates

GitHub Actions are pinned to immutable commits resolved from official release tags.
Dependabot proposes updates weekly; maintainers review upstream release notes and
runner/runtime compatibility before merging. No automatic Codex review or automatic
merge is enabled. Python package metadata retains a supported setuptools minimum;
there are no runtime Python dependencies. Packaging tooling is checked on every
supported Python version instead of promising a fully reproducible dependency lock.

Keep Python 3.11–3.13, local demonstrations, installed-wheel inspection, Compose,
pinned-proxy Host/Origin tests and packaged skills/examples checks when updating.
The image workflow remains explicitly dispatched. A base-image change additionally
requires native boot/model/restart and state/scheduler upgrade acceptance; passing
package tests alone does not establish live provider or runtime compatibility.
Review image tags and digests together, retain upstream license notices, and record
the exact resulting image. Public publishing is separate from dependency updates.
