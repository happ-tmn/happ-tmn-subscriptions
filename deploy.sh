#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

# Run safely from Android Downloads: Git itself works only in Termux's internal storage.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
OWNER='happ-tmn'
REPO='happ-tmn-subscriptions'
FULL="$OWNER/$REPO"

for bin in git gh python; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "Установи пакет: pkg install $bin -y"
    exit 1
  fi
done

if [ ! -s "$ROOT/sources.private.txt" ]; then
  echo '❌ Источники пусты: sources.private.txt'
  exit 1
fi

USER_LOGIN="$(gh api user --jq .login)"
if [ "$USER_LOGIN" != "$OWNER" ]; then
  echo "❌ Активен аккаунт $USER_LOGIN, нужен $OWNER"
  echo "gh auth switch -h github.com -u $OWNER"
  exit 1
fi

TMP_BASE="${TMPDIR:-${PREFIX:-/data/data/com.termux/files/usr}/tmp}"
mkdir -p "$TMP_BASE"
WORK="$(mktemp -d "$TMP_BASE/happ-tmn-deploy.XXXXXXXX")"
trap 'rm -rf "$WORK"' EXIT
DEST="$WORK/repo"

IS_EXISTING=0
if gh repo view "$FULL" >/dev/null 2>&1; then
  IS_EXISTING=1
  echo "📂 Репозиторий $FULL найден: обновляю существующий проект"
  git -c credential.helper= -c credential.helper='!gh auth git-credential' \
    clone --branch main "https://github.com/$FULL.git" "$DEST"
else
  echo "📂 Создаю новый репозиторий $FULL"
  mkdir -p "$DEST"
  git -C "$DEST" init -b main
fi

FILES=(
  '.github/workflows/refresh.yml' '.gitignore' 'README.md'
  'collector.py' 'deploy.sh' 'update_sources.sh'
  'tests/test_collector.py' 'sub/.gitkeep' 'assets/yinglong_banner.png'
)
for file in "${FILES[@]}"; do
  if [ ! -f "$ROOT/$file" ]; then
    echo "❌ Не найден $file в папке проекта"
    exit 1
  fi
  mkdir -p "$(dirname "$DEST/$file")"
  cp "$ROOT/$file" "$DEST/$file"
done

# Require strong ignore rules even when someone later changes the project.
if ! git -C "$DEST" check-ignore -q sources.private.txt; then
  echo '❌ sources.private.txt должен быть исключён из Git'
  exit 1
fi

git -C "$DEST" config user.name "$OWNER"
git -C "$DEST" config user.email '352484844+happ-tmn@users.noreply.github.com'
git -C "$DEST" config --local --replace-all credential.helper ''
git -C "$DEST" config --local --add credential.helper '!gh auth git-credential'
git -C "$DEST" add -- "${FILES[@]}"

if ! git -C "$DEST" diff --cached --quiet; then
  git -C "$DEST" commit -m 'Update subscription collector and Yinglong README'
else
  echo '✅ Код уже актуален'
fi

if [ "$IS_EXISTING" -eq 1 ]; then
  git -C "$DEST" push origin main
else
  gh repo create "$FULL" --public --source="$DEST" --remote=origin --push \
    --description 'Happ TMN - auto-updating subscription collector'
fi

# URL list is stored as an Actions secret, never committed.
gh secret set SOURCES_TXT -R "$FULL" < "$ROOT/sources.private.txt"
echo '✅ Доноры сохранены в Actions Secret SOURCES_TXT'

if gh workflow run refresh.yml -R "$FULL"; then
  echo '✅ Запрошен первый/повторный запуск Actions'
else
  echo '⚠️ Нажми Run workflow в GitHub Actions вручную'
fi

echo "✅ Репозиторий: https://github.com/$FULL"
echo "📄 TXT: https://raw.githubusercontent.com/$FULL/main/sub/all.txt"
echo "💎 Vision: https://raw.githubusercontent.com/$FULL/main/sub/vless/reality-vision.txt"
