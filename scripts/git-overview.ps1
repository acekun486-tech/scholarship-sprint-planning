<#
.SYNOPSIS
    查看当前 Git 仓库的提交历史、分支和标签。

.DESCRIPTION
    一条命令汇总：
      1. 所有分支可达的提交历史（含合并关系、分支和标签装饰）
      2. 本地与远程分支
      3. 标签及其说明
    脚本只读取本地 .git，不会修改仓库，也不会联网。

.PARAMETER RepoPath
    仓库路径，默认是当前目录。脚本会自动向上查找仓库根目录。

.PARAMETER MaxCommits
    历史最多显示多少条，默认 20；设为 0 表示显示全部。

.EXAMPLE
    .\scripts\git-overview.ps1

.EXAMPLE
    .\scripts\git-overview.ps1 -RepoPath "D:\cxdownload\scholarship-sprint-planning (1)" -MaxCommits 50

.EXAMPLE
    .\scripts\git-overview.ps1 -MaxCommits 0
#>
[CmdletBinding()]
param(
    [string]$RepoPath = (Get-Location).Path,
    [int]$MaxCommits = 20
)

$ErrorActionPreference = "Stop"

# 让中文提交信息和脚本提示在 Windows PowerShell 中正常显示
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    # 某些非控制台宿主不支持修改编码，忽略即可
}

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 64) -ForegroundColor DarkGray
    Write-Host $Title -ForegroundColor Cyan
    Write-Host ("=" * 64) -ForegroundColor DarkGray
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "未找到 git，请先安装 Git for Windows。" -ForegroundColor Red
    exit 1
}

# 仓库检查：临时关闭 Stop，避免 git 的 stderr 直接抛出 NativeCommandError
$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "SilentlyContinue"
$root = git -C $RepoPath rev-parse --show-toplevel 2>$null
$gitExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference

if ($gitExitCode -ne 0 -or [string]::IsNullOrWhiteSpace($root)) {
    Write-Host "当前目录不是 Git 仓库：$RepoPath" -ForegroundColor Red
    Write-Host "请进入仓库目录，或用 -RepoPath 指定仓库根目录：" -ForegroundColor Yellow
    Write-Host '  .\scripts\git-overview.ps1 -RepoPath "D:\path\to\repo"' -ForegroundColor Yellow
    exit 1
}

$branch = git -C $root branch --show-current
if ([string]::IsNullOrWhiteSpace($branch)) {
    $branch = "(detached HEAD)"
}

$head = git -C $root rev-parse --short HEAD
$describe = git -C $root describe --tags --always 2>$null
if ($LASTEXITCODE -ne 0) {
    $describe = "-"
}
$commitCount = git -C $root rev-list --all --count
$statusLines = git -C $root status -sb

Write-Section "仓库概况"
Write-Host "路径：      $root"
Write-Host "当前分支：  $branch"
Write-Host "HEAD：      $head"
Write-Host "相对标签：  $describe"
Write-Host "提交总数：  $commitCount（所有分支和标签可达的提交）"
Write-Host "工作区：    $($statusLines -join ' | ')"

Write-Section "1. 提交历史（所有分支，最近 $MaxCommits 条；0 表示全部）"
if ($MaxCommits -gt 0) {
    git -C $root --no-pager log --all --oneline --graph --decorate -n $MaxCommits
} else {
    git -C $root --no-pager log --all --oneline --graph --decorate
}

Write-Section "2. 分支（本地 + 远程）"
git -C $root branch --no-color -a -vv

Write-Section "3. 标签"
$tagOutput = git -C $root tag -n --sort=-creatordate
if ([string]::IsNullOrWhiteSpace(($tagOutput -join ""))) {
    Write-Host "（当前仓库还没有标签）" -ForegroundColor Yellow
} else {
    $tagOutput
}
