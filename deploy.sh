#!/bin/bash
# ⛳ OKCaddie deployment helper script (option style)

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUCKET_URL="${BUCKET_URL:-gs://ok-project-assets/okcaddie}"
IMAGES_DIR="app/static/images"
CONTENT_DIR="app/content"
GUIDE_DIR="app/content/guides"
GCP_PROJECT_ID="${GCP_PROJECT_ID:-starful-258005}"
COMMIT_MSG="update: auto-generated courses, guides & UI $(date '+%Y-%m-%d %H:%M') (Admin Sync)"

MODE="full"
DO_GIT=false
DO_CLOUD_DEPLOY=false
CONTENT_LIMIT="${CONTENT_LIMIT:-10}"
GUIDE_LIMIT="${GUIDE_LIMIT:-3}"
NEW_COURSE=0
NEW_GUIDE=0
MISSING=0

print_step() { echo ""; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
print_err()  { echo -e "${RED}  ❌ $1${NC}"; }
print_info() { echo -e "  ℹ️  $1"; }

usage() {
    cat <<'EOF'
Usage: ./deploy.sh [MODE] [OPTIONS]

Modes (default: full)
  --full           Sync images + generate content + image process + build + upload
  --content-only   Generate course/guide markdown + build only
  --deploy-only    Trigger Cloud Build deploy only

Options
  --with-git       Commit and push generated changes
  --with-deploy    Trigger deploy after selected mode
  --help           Show this help

Environment overrides
  CONTENT_LIMIT    Default: 10
  GUIDE_LIMIT      Default: 3
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        print_err "Missing required command: $1"
        exit 1
    fi
}

check_env() {
    print_step "STEP 0  |  환경 체크"
    [ ! -f ".env" ] && { print_err ".env 없음"; exit 1; }
    print_ok ".env 확인"
}

sync_cloud_images_to_local() {
    print_step "STEP A  |  GCS 최신 이미지 가져오기"
    mkdir -p "$IMAGES_DIR"
    gsutil -m rsync -r "$BUCKET_URL" "$IMAGES_DIR"
    print_ok "클라우드 이미지 동기화 완료"
}

generate_content() {
    print_step "STEP B  |  코스/가이드 컨텐츠 생성"
    local before_course=0
    [ -d "$CONTENT_DIR" ] && before_course=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
    mkdir -p "$GUIDE_DIR"
    local before_guide
    before_guide=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')

    python3 script/course_generator.py "$CONTENT_LIMIT"
    python3 script/guide_generator.py "$GUIDE_LIMIT"

    local after_course
    after_course=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
    local after_guide
    after_guide=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')
    NEW_COURSE=$(( after_course - before_course ))
    NEW_GUIDE=$(( after_guide - before_guide ))
    print_ok "컨텐츠 생성 완료 (코스 +${NEW_COURSE}, 가이드 +${NEW_GUIDE})"
}

process_images() {
    print_step "STEP C  |  이미지 수집/최적화"
    MISSING=0
    _places=0
    if grep -qE '^[[:space:]]*GOOGLE_PLACES_API_KEY=' .env 2>/dev/null; then
        _places=1
    elif grep -qE '^[[:space:]]*GOOGLE_CLOUD_PROJECT=' .env 2>/dev/null \
        || grep -qE '^[[:space:]]*GCP_PROJECT_ID=' .env 2>/dev/null; then
        # fetch_images: 프로젝트만 있어도 시크릿 GOOGLE_PLACES_API_KEY 기본 조회
        _places=1
    fi

    if [ "$_places" -eq 1 ]; then
        for md_file in "$CONTENT_DIR"/*_en.md; do
            [ -f "$md_file" ] || continue
            base=$(basename "$md_file" _en.md)
            if [ ! -f "${IMAGES_DIR}/${base}.jpg" ]; then
                MISSING=$((MISSING + 1))
            fi
        done

        if [ "$MISSING" -gt 0 ]; then
            print_info "이미지 없는 골프장: ${MISSING}개"
            python3 script/fetch_images.py
        else
            print_ok "모든 코스 이미지 존재"
        fi
    else
        print_warn "Places 키 없음(Secret Manager 또는 GOOGLE_PLACES_API_KEY) → 이미지 수집 건너뜀"
    fi

    python3 script/optimize_images.py
    print_ok "이미지 처리 완료"
}

build_data() {
    print_step "STEP D  |  데이터 빌드"
    python3 script/build_data.py
    print_ok "데이터 빌드 완료"
}

upload_images() {
    print_step "STEP E  |  GCS 최종 업로드"
    gsutil -m rsync -r "$IMAGES_DIR" "$BUCKET_URL"
    print_ok "GCS 업로드 완료"
}

git_push_changes() {
    print_step "STEP F  |  GitHub Push"
    git add .
    if ! git diff-index --quiet HEAD --; then
        git commit -m "$COMMIT_MSG"
        git push origin main
        print_ok "GitHub push 완료"
    else
        print_warn "변경 없음"
    fi
}

deploy_cloud_run() {
    print_step "STEP G  |  Cloud Build 배포"
    gcloud builds submit --project "$GCP_PROJECT_ID"
    print_ok "Cloud Run 배포 완료"
}

run_smoke_test() {
    print_step "STEP H  |  배포 스모크 테스트"
    python3 script/smoke_test.py "https://okcaddie.net"
    print_ok "스모크 테스트 통과"
}

for arg in "$@"; do
    case "$arg" in
        --full) MODE="full" ;;
        --content-only) MODE="content-only" ;;
        --deploy-only) MODE="deploy-only" ;;
        --with-git) DO_GIT=true ;;
        --with-deploy) DO_CLOUD_DEPLOY=true ;;
        --help|-h) usage; exit 0 ;;
        *)
            print_err "Unknown argument: $arg"
            usage
            exit 1
            ;;
    esac
done

cd "$PROJECT_ROOT"
START_TIME=$SECONDS
if [ -t 1 ]; then clear; fi

print_info "Mode: $MODE"
print_info "Limits: content=${CONTENT_LIMIT}, guide=${GUIDE_LIMIT}"
check_env
require_cmd python3
require_cmd gcloud

case "$MODE" in
    full)
        require_cmd gsutil
        sync_cloud_images_to_local
        generate_content
        process_images
        build_data
        upload_images
        run_smoke_test
        ;;
    content-only)
        generate_content
        build_data
        ;;
    deploy-only)
        DO_CLOUD_DEPLOY=true
        ;;
esac

if [ "$DO_GIT" = true ]; then
    require_cmd git
    git_push_changes
fi

if [ "$DO_CLOUD_DEPLOY" = true ]; then
    deploy_cloud_run
fi

ELAPSED=$(( SECONDS - START_TIME ))
print_step "DONE  |  완료 요약"
echo -e "${BOLD}${GREEN}  🎉 스크립트 실행 완료${NC}"
echo -e "  ⏱️  총 소요 시간  : $(( ELAPSED / 60 ))분 $(( ELAPSED % 60 ))초"
echo -e "  📄 신규 코스     : +${NEW_COURSE}개"
echo -e "  📖 신규 가이드   : +${NEW_GUIDE}개"
echo ""

if [[ "$OSTYPE" == "darwin"* ]] && [[ "${AUTO_REGISTER_RUN:-0}" != "1" ]]; then
    osascript -e 'display notification "OKCaddie 배포 완료!" with title "Deploy"' 2>/dev/null || true
fi