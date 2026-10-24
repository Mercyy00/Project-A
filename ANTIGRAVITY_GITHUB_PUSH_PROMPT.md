# Antigravity CLI task: review and push Project A to GitHub

You are operating in the existing `Project - A` repository. The team lead wants the current JARVIS work reviewed and pushed to the repository's configured GitHub remote.

1. Start with `git status --short --branch`, `git diff --stat`, `git diff --check`, and `git remote -v`. Read `AGENTS.md` and preserve every existing user change. Do not reset, checkout over, stash-drop, clean, delete, or rewrite existing work.
2. Review the full staged and unstaged diffs, including the JARVIS UI, voice, browser/tools, creator, messaging, and vision changes. Confirm the new UI preserves the existing element IDs and event wiring. Do not claim a feature works unless the code and checks support that claim.
3. Keep machine-local files and secrets out of Git. Never stage `.env`, credentials, tokens, local databases, logs, caches, virtual environments, temp audio/vision, or generated personal files. `.env.example` may be included only after confirming it contains placeholders, not real credentials. Do not force-add ignored files.
4. Run the project's checks (`pytest -q` and `git diff --check`) if dependencies/environment allow. Report failures accurately and fix only issues you can safely fix without discarding existing work. Review `git status` again afterward.
5. Stage only reviewed, intentional project source, tests, documentation, and this push prompt. Inspect `git diff --cached` and run a secret scan on the staged diff before committing. If any uncertain file, credential, unrelated change, or failing check remains, stop and report exactly what needs the team lead's decision; do not silently omit their work.
6. Use the configured `origin` remote and the existing branch/tracking setup. Do not invent a remote URL, create a replacement repository, force-push, or overwrite remote history. If the branch has no upstream or pushing `main` is rejected/non-fast-forward, stop and explain the safe next step rather than forcing it.
7. If review and checks are clean, create one descriptive commit for the reviewed JARVIS changes, then push the current branch to `origin`. Finish with the commit hash, branch, push result, checks run, and any remaining caveats.

The team lead explicitly plans to use Antigravity CLI to push. Do not ask them to repeat that instruction; only pause for a concrete unresolved risk such as a secret, destructive change, or remote-history conflict.
