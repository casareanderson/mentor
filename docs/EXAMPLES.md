# mentor — worked examples

## 1. Review the current working-tree changes

```bash
git diff | mentor diff -
```

## 2. Review a saved patch

```bash
git format-patch -1 --stdout > pr.patch
mentor diff pr.patch
```

## 3. Review a GitHub PR

```bash
GITHUB_TOKEN=ghp_... mentor pr casareanderson/sieve#23
```

## 4. In a GitHub Actions PR check

```yaml
name: mentor review
on:
  pull_request:

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - run: pip install requests
      - name: mentor
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
        run: |
          git diff origin/${{ github.base_ref }}...HEAD > /tmp/diff.patch
          python review.py diff /tmp/diff.patch
```

`mentor` exits non-zero only when the model is unreachable or the diff can't be read — not on a `changes` verdict —
so the review never fails your build on its own judgement.

## 5. Review every PR on a repo on a timer

```bash
for n in $(gh pr list --json number --jq '.[].number'); do
  gh pr diff "$n" > "/tmp/pr-$n.patch"
  GITHUB_TOKEN=$GH_TOKEN ./mentor pr "owner/repo#$n"
done
```
