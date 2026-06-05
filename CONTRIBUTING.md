# Contributing — PR & Commit Rules

This project follows a strict commit-and-PR discipline. Every change must go through this workflow.

## Commit Format

Each commit message must follow the **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Allowed `type` values

| Type | Use when |
|---|---|
| `feat` | Adding a new feature |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `docs` | Documentation only |
| `test` | Adding or fixing tests |
| `perf` | Performance improvement |
| `chore` | Build, CI, tooling, or maintenance |
| `style` | Formatting, whitespace, semicolons (no logic change) |

### `scope` rules

- **Be specific.** `fix(editor)` is better than `fix(frontend)`.
- Match the affected module: `fix(parser)`, `feat(extractor)`, `refactor(api)`.
- For cross-cutting changes, use the dominant module.

### `subject` rules

- Imperative mood: "add", not "added" or "adds"
- Lowercase first letter
- No period at the end
- Max 72 characters

## Required Commit Body — 4 Mandatory Sections

Every commit body **must** contain these four sections in this order:

```
① 标题: <one-line summary>
② 功能描述: <what this commit does and how to use it>
③ 实现思路: <technical choices and core implementation logic>
④ 测试方式: <how to verify this commit works>
```

### Example — Good Commit

```
fix(editor): fix editor panel sizing and Monaco rendering issues

① 标题: 修复 EditorPage 中两栏高度截断、Monaco minimap 与 loading 重叠的问题
② 功能描述: 让 YAML 编辑器和剧本预览两个面板都填满视口可用空间，
   YAML 内容完整可见，Monaco 不再显示重叠的缩略图和加载提示。
③ 实现思路:
   - EditorPage: 用原生 flex 替换 Ant Design Row/Col
   - 父容器 height: calc(100vh - 64px), 子层 flex-1 + min-h-0
   - MonacoYaml: 关闭 minimap, 移除 loading prop, 显式 width=100%
④ 测试方式:
   - npm run build 编译通过
   - 浏览器打开 /editor, 验证两栏高度填满视口
   - 拖动窗口大小, 验证面板跟随自适应
```

### Example — Bad Commit (Will Be Rejected)

```
fix: fix some stuff

- changed a few files
- works now
```

Reasons: no scope, vague subject, missing 4 sections, no body detail.

## PR (Pull Request) Rules

1. **One commit = one thing.** Do not bundle unrelated changes.
2. **Granularity.** Split large features into multiple small commits.
3. **Title:** one-line summary of what the PR adds or changes.
4. **Description:** include the 4 mandatory sections (same as commit body).
5. **Test coverage.** Every PR must include or update tests.
6. **Code must run after merge.** The `master` branch must always be in a runnable state.
7. **Atomic commits** preferred over squash merges.

## Branch Naming

```
master           Main branch — always runnable
feat/<name>      New feature in development
fix/<name>       Bug fix
chore/<name>     Tooling, config, maintenance
docs/<name>      Documentation
refactor/<name>  Code refactor
```

## Workflow

```
1. 切到 master:   git checkout master
2. 拉取最新:       git pull
3. 开辟分支:       git checkout -b fix/your-fix-name
4. 开发 + 提交:    # Make small atomic commits, each with 4-section body
                  git add <files>
                  git commit -m "..."
5. 测试:          # Run all relevant tests before merging
6. 合并:          git checkout master
                  git merge fix/your-fix-name --no-ff
```

## Pre-merge Checklist

Before merging any branch back to `master`, verify:

- [ ] All commits follow the 4-section format
- [ ] All tests pass (`pytest tests/` and `mvn test`)
- [ ] Code is runnable (no broken imports, no missing config)
- [ ] No secrets committed (`.env` is git-ignored)
- [ ] TypeScript / Python type checks pass
- [ ] No unrelated changes included

## Enforcement

PRs and commits that violate these rules will be asked to be amended before merge. Maintainers should hold the line on quality.
