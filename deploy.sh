#!/bin/bash
# ⛳ OKCaddie 자동 배포 파이프라인 (Safe Admin Sync 버전)
# 실행: ./deploy.sh

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BUCKET_URL="gs://ok-project-assets/okcaddie"
IMAGES_DIR="app/static/images"
COMMIT_MSG="update: auto-generated courses, guides & UI $(date '+%Y-%m-%d %H:%M') (Admin Sync)"

print_step() { echo ""; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
print_err()  { echo -e "${RED}  ❌ $1${NC}"; }
print_info() { echo -e "  ℹ️  $1"; }

clear
echo ""
echo -e "${BOLD}${CYAN}  ⛳  OKCaddie 자동 배포 파이프라인 (Safe Sync)${NC}"
echo -e "  $(date '+%Y년 %m월 %d일 %H:%M:%S') 시작"
echo ""
START_TIME=$SECONDS

# ── STEP 0: 환경 체크 및 이미지 역동기화 ─────
print_step "STEP 0 / 7  |  환경 체크 및 관리자 데이터 동기화"
cd "$PROJECT_ROOT"

[ ! -f ".env" ] && { print_err ".env 없음"; exit 1; }
print_ok ".env 확인"

# .env 로드 (배포용 키 주입에 사용)
set -a
source ".env"
set +a

# gsutil 설치 확인
command -v gsutil &>/dev/null || { print_err "gsutil 없음"; exit 1; }

# [보호 로직 추가] 알바생이 올린 최신 사진 가져오기
mkdir -p "$IMAGES_DIR"
print_info "클라우드($BUCKET_URL)에서 최신 사진 가져오는 중..."
gsutil -m rsync -r "$BUCKET_URL" "$IMAGES_DIR"
print_ok "클라우드 이미지 동기화 완료 (알바생 업로드분 보호)"

# ── STEP 1: AI 컨텐츠 생성 (코스 & 가이드) ──
print_step "STEP 1 / 7  |  AI 컨텐츠 생성 (Gemini API)"

CONTENT_DIR="app/content"
BEFORE_COURSE=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
GUIDE_DIR="app/content/guides"
mkdir -p "$GUIDE_DIR"
BEFORE_GUIDE=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')

print_info "1-1. 골프장 코스 컨텐츠 생성 중..."
python3 script/course_generator.py

print_info "1-2. 골프 가이드 컨텐츠 생성 중..."
python3 script/guide_generator.py 5

AFTER_COURSE=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
AFTER_GUIDE=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')
NEW_COURSE=$(( AFTER_COURSE - BEFORE_COURSE ))
NEW_GUIDE=$(( AFTER_GUIDE - BEFORE_GUIDE ))

print_ok "컨텐츠 생성 완료!"

# ── STEP 2: 이미지 수집 및 최적화 ────────────
print_step "STEP 2 / 7  |  이미지 수집 및 최적화"

MISSING=0
if grep -q "GOOGLE_PLACES_API_KEY" .env; then
    # STEP 0에서 최신 이미지를 가져왔으므로, 알바생이 올린 사진은 여기서 누락된 것으로 간주되지 않습니다.
    for md_file in "$CONTENT_DIR"/*_en.md; do
        [ -f "$md_file" ] || continue
        base=$(basename "$md_file" _en.md)
        if [ ! -f "${IMAGES_DIR}/${base}.jpg" ]; then
            MISSING=$((MISSING + 1))
        fi
    done

    if [ "$MISSING" -gt 0 ]; then
        print_info "이미지 없는 골프장: ${MISSING}개 → 수집 시작"
        python3 script/fetch_images.py
    else
        print_ok "모든 코스 이미지 존재 (관리자 사진 포함)"
    fi
else
    print_warn "GOOGLE_PLACES_API_KEY 없음 → 이미지 수집 건너뜀"
fi

print_info "이미지 규격 검사 및 최적화 실행..."
python3 script/optimize_images.py
print_ok "이미지 처리 완료"

# ── STEP 3: 데이터 빌드 및 GCS 동기화 ───────
print_step "STEP 3 / 7  |  데이터 빌드 및 GCS 최종 업로드"

print_info "JSON 및 Sitemap 갱신 중..."
python3 script/build_data.py
print_ok "데이터 빌드 완료"

print_info "GCS 버킷으로 이미지 최종 전송 중..."
# 위에서 로컬로 사진을 다 가져왔기 때문에 안전하게 동기화합니다.
gsutil -m rsync -r "$IMAGES_DIR" "$BUCKET_URL"
print_ok "GCS 업로드 완료"

# ── STEP 4: Git Push ───────────────────────
print_step "STEP 4 / 7  |  GitHub Push"

GIT_STATUS=$(git status --porcelain)
if [ -z "$GIT_STATUS" ]; then
    print_warn "변경 없음"
else
    git add .
    git commit -m "$COMMIT_MSG"
    git push origin main
    print_ok "GitHub push 완료 (최신 사진 정보 포함)"
fi

# ── STEP 5: Cloud Build & Cloud Run ───────
print_step "STEP 5 / 7  |  Cloud Build & Cloud Run 배포"
print_info "Google Cloud 배포 시작..."
if [ -z "${GOOGLE_MAPS_JS_API_KEY:-}" ]; then
    print_err "GOOGLE_MAPS_JS_API_KEY 없음 → Cloud Build substitution(_GOOGLE_MAPS_JS_API_KEY) 불가"
    exit 1
fi

gcloud builds submit \
    --project starful-258005 \
    --substitutions="_GOOGLE_MAPS_JS_API_KEY=${GOOGLE_MAPS_JS_API_KEY}"
print_ok "Cloud Run 배포 완료"

# ── STEP 6: 완료 요약 ──────────────────────
print_step "STEP 6 / 7  |  완료 요약"

ELAPSED=$(( SECONDS - START_TIME ))
echo ""
echo -e "${BOLD}${GREEN}  🎉 전체 파이프라인 완료!${NC}"
echo ""
echo -e "  ⏱️  총 소요 시간  : $(( ELAPSED / 60 ))분 $(( ELAPSED % 60 ))초"
echo -e "  📄 신규 코스     : +${NEW_COURSE}개"
echo -e "  📖 신규 가이드   : +${NEW_GUIDE}개"
echo -e "  🌐 라이브 주소   : https://okcaddie.net"
echo ""

if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e 'display notification "OKCaddie 배포 완료!" with title "Safe Deploy"' 2>/dev/null || true
fi
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""