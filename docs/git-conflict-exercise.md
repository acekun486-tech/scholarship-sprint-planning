# 合并冲突演练记录（实验三 步骤 7）

## 演练目标

验证 GitHub Flow 下“两人修改同一文件同一行 → 后合并方产生冲突 → 手动解决 → 提交合并结果”的完整过程，确认团队不会用 `git push --force` 覆盖他人提交。

## 参与分支与提交

| 分支 | 修改内容 | 提交 |
|---|---|---|
| `feature/readme-a` | README 第一行改为“（实验三协作版）” | `b879d2d docs: 在分支 A 更新 README 标题` |
| `feature/readme-b` | README 第一行改为“（Sprint 1 发布版）” | `d52d8dd docs: 在分支 B 更新 README 标题` |

两个分支均从 `main` 的 `121baa0`（质量门禁合并提交）拉出。

## 操作过程

```powershell
# 分支 A：修改 README 第一行并提交
git checkout -b feature/readme-a main
# 编辑 README.md 第一行
git commit -am "docs: 在分支 A 更新 README 标题"

# 分支 B：从同一基线修改同一行
git checkout main
git checkout -b feature/readme-b main
# 编辑 README.md 第一行（不同内容）
git commit -am "docs: 在分支 B 更新 README 标题"

# 先合并 A，再合并 B
git checkout main
git merge --no-ff feature/readme-a -m "merge: 合入 README 标题分支 A"
git merge --no-ff feature/readme-b -m "merge: 合入 README 标题分支 B"
```

第二次合并输出：

```text
Auto-merging README.md
CONFLICT (content): Merge conflict in README.md
Automatic merge failed; fix conflicts and then commit the result.
```

## 冲突内容

`README.md` 第一行出现冲突标记：

```text
<<<<<<< HEAD
# 高校学工平台——奖助学金管理子系统（实验三协作版）
=======
# 高校学工平台——奖助学金管理子系统（Sprint 1 发布版）
>>>>>>> feature/readme-b
```

## 解决方式

手动编辑第一行，保留两个分支的发布信息并合并为一个标题：

```markdown
# 高校学工平台——奖助学金管理子系统（v1.0.0 · Sprint 1 发布版）
```

删除全部 `<<<<<<<`、`=======`、`>>>>>>>` 标记后执行：

```powershell
git add README.md
git commit -m "merge: 解决 README 合并冲突"
```

## 结果验证

| 检查项 | 结果 |
|---|---|
| 冲突已解决 | `git status` 无 `UU` 文件；README 无冲突标记 |
| 合并提交 | `6b5d0d1 merge: 解决 README 合并冲突`（双父提交） |
| 分支历史 | `git log --oneline --graph` 显示 A、B 两个分支各自合并后汇入 `main` |
| 内容正确 | README 第一行为合并后的标题，其余内容未丢失 |
| 回归测试 | README 变更不影响代码，`pytest -q` 仍为 40 passed |
| 强推 | 全程未使用 `git push --force` / `--force-with-lease` |

## 经验与规则

1. 冲突集中在同一文件的同一行时，Git 无法自动判断保留哪一版，必须人工阅读双方意图。
2. 解决冲突时不要直接选择“全部接受某一方”，应先理解两个分支为什么修改，再决定保留、合并或重写。
3. 冲突解决后必须重新运行受影响范围的测试；本次只改 README，仍执行全量测试确认无意外影响。
4. 禁止强推覆盖远端历史；如确需回退，使用新的 `revert` 提交并说明原因。
5. 减少冲突的根本办法是小步提交、及时同步 `main`、按功能拆分文件与段落。
