#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
OWNER='happ-tmn'
REPO='happ-tmn-subscriptions'
FULL="$OWNER/$REPO"
for bin in git gh python; do command -v "$bin" >/dev/null || { echo "Сначала установи: pkg install git gh python -y"; exit 1; }; done
[ -s sources.private.txt ] || { echo 'Нет файла sources.private.txt'; exit 1; }
USER_LOGIN="$(gh api user --jq .login)"
if [ "$USER_LOGIN" != "$OWNER" ]; then
  echo "Сейчас в GitHub CLI аккаунт: $USER_LOGIN; нужен: $OWNER"
  echo "Выполни: gh auth login -h github.com --git-protocol https --web"
  echo "Затем: gh auth switch -h github.com -u $OWNER"
  exit 1
fi
if [ -d .git ]; then
  echo 'Git уже инициализирован в папке проекта'
else
  git init -b main
fi
git config --local user.name "${OWNER}"
git config --local user.email '352484844+happ-tmn@users.noreply.github.com'
# Isolate this repository from cached credentials of other GitHub accounts.
git config --local --replace-all credential.helper ''
git config --local --add credential.helper '!gh auth git-credential'
# Never stage secret files; verify Git's ignore rules.
if ! git check-ignore -q sources.private.txt; then
  echo 'ОШИБКА: sources.private.txt не исключён из Git'
  exit 1
fi
git add .github/workflows/refresh.yml collector.py tests README.md deploy.sh update_sources.sh .gitignore sub/.gitkeep
if ! git diff --cached --quiet; then
  git commit -m 'Initial subscription collector for happ-tmn'
fi
if gh repo view "$FULL" >/dev/null 2>&1; then
  echo "Репозиторий $FULL уже существует. Проверяю remote."
  if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "https://github.com/$FULL.git"
  else
    git remote add origin "https://github.com/$FULL.git"
  fi
  git push -u origin main
else
  gh repo create "$FULL" --public --source=. --remote=origin --push --description 'Automated public proxy subscription lists for happ_tmn'
fi
# stdin prevents secret from appearing in shell args/logs.
gh secret set SOURCES_TXT -R "$FULL" < sources.private.txt
printf '%s\n' 'Четыре источника помещены в GitHub Actions Secret (адреса не опубликованы).'
if ! gh workflow run refresh.yml -R "$FULL"; then
  echo 'Workflow пока не запустился. Открой GitHub Actions и выбери Run workflow вручную.'
fi
printf '%s\n' 'Подписки появятся после первого успешного GitHub Actions запуска:'
printf 'https://raw.githubusercontent.com/%s/main/sub/all.txt\n' "$FULL"
printf 'https://raw.githubusercontent.com/%s/main/sub/vless/reality-vision.txt\n' "$FULL"
