#!/usr/bin/env bash
# Publish the web/ folder to AWS Amplify Hosting (a manual deployment: the app isn't connected to Git).
#
# GitHub Actions runs it after the tests pass (.github/workflows/deploy.yml). Plan B, from a laptop:
#   export AWS_PROFILE=refugio
#   AMPLIFY_APP_ID=$(terraform -chdir=infra output -raw amplify_app_id) ./deploy/deploy.sh
#
# Steps: copy web/ -> add config.js with the PRODUCTION key -> zip -> upload -> wait until it's live.
set -euo pipefail

APP_ID="${AMPLIFY_APP_ID:?Set AMPLIFY_APP_ID (terraform -chdir=infra output -raw amplify_app_id)}"
BRANCH="${AMPLIFY_BRANCH:-main}"
REGION="${AWS_REGION:-us-west-2}"
KEY_NAME="${LOCATION_KEY_NAME:-refugio-web-prod}"
BUILD="deploy/build" # git-ignored scratch folder

cd "$(dirname "$0")/.." # always work from the repository root

echo "1/5 Copying web/ to $BUILD/site"
rm -rf "$BUILD" && mkdir -p "$BUILD/site"
cp -R web/. "$BUILD/site/"
rm -f "$BUILD/site/config.js" # never ship a laptop's localhost-only key

echo "2/5 Writing config.js with the production API key ($KEY_NAME)"
KEY=$(aws location describe-key --key-name "$KEY_NAME" --region "$REGION" --query Key --output text)
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then echo "::add-mask::$KEY"; fi # keep it out of the build logs
printf "window.REFUGIO_CONFIG = { region: '%s', apiKey: '%s' };\n" "$REGION" "$KEY" >"$BUILD/site/config.js"

echo "3/5 Zipping the site"
(cd "$BUILD/site" && python3 -c 'import shutil; shutil.make_archive("../site", "zip", ".")')

echo "4/5 Uploading to Amplify (app $APP_ID, branch $BRANCH)"
read -r JOB_ID UPLOAD_URL < <(aws amplify create-deployment --app-id "$APP_ID" --branch-name "$BRANCH" \
  --region "$REGION" --query '[jobId, zipUploadUrl]' --output text)
curl -sSf -X PUT -H "Content-Type: application/zip" --upload-file "$BUILD/site.zip" "$UPLOAD_URL" >/dev/null
aws amplify start-deployment --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB_ID" \
  --region "$REGION" >/dev/null

echo "5/5 Waiting for Amplify to publish job $JOB_ID"
STATUS="PENDING"
for _ in $(seq 1 60); do
  STATUS=$(aws amplify get-job --app-id "$APP_ID" --branch-name "$BRANCH" --job-id "$JOB_ID" \
    --region "$REGION" --query 'job.summary.status' --output text)
  case "$STATUS" in
    SUCCEED) break ;;
    FAILED | CANCELLED) echo "Amplify job $STATUS" >&2; exit 1 ;;
  esac
  sleep 5
done
[[ "$STATUS" == "SUCCEED" ]] || { echo "Timed out waiting for Amplify (last status: $STATUS)" >&2; exit 1; }

SITE_URL="https://$BRANCH.$APP_ID.amplifyapp.com" # Amplify's default domain is <app id>.amplifyapp.com
echo "Live: $SITE_URL"
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then echo "site_url=$SITE_URL" >>"$GITHUB_OUTPUT"; fi
