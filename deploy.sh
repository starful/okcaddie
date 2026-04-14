#!/bin/bash
# ⛳ OKCaddie 자동 배포 파이프라인 (코스 & 가이드 생성 + GCS 동기화)
# 실행: ./deploy.sh

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMMIT_MSG="update: auto-generated courses, guides & UI $(date '+%Y-%m-%d %H:%M')"

print_step() { echo ""; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
print_warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
print_err()  { echo -e "${RED}  ❌ $1${NC}"; }
print_info() { echo -e "  ℹ️  $1"; }

clear
echo ""
echo -e "${BOLD}${CYAN}  ⛳  OKCaddie 자동 배포 파이프라인${NC}"
echo -e "  $(date '+%Y년 %m월 %d일 %H:%M:%S') 시작"
echo ""
START_TIME=$SECONDS

# ── STEP 0: 환경 체크 ──────────────────────
print_step "STEP 0 / 6  |  환경 체크"
cd "$PROJECT_ROOT"

[ ! -f ".env" ] && { print_err ".env 없음"; exit 1; }
print_ok ".env 확인"

grep -q "GEMINI_API_KEY" .env || { print_err "GEMINI_API_KEY 없음"; exit 1; }
print_ok "API 키 확인"

# 필요한 스크립트 존재 여부 확인
[ ! -f "script/course_generator.py" ] && { print_err "course_generator.py 없음"; exit 1; }
[ ! -f "script/guide_generator.py" ] && { print_err "guide_generator.py 없음"; exit 1; }

GUIDE_CSV="script/csv/guides.csv"
[ ! -f "$GUIDE_CSV" ] && { print_warn "가이드 CSV 없음: $GUIDE_CSV"; }

# ── STEP 1: AI 컨텐츠 생성 (코스 & 가이드) ──
print_step "STEP 1 / 6  |  AI 컨텐츠 생성 (Gemini API)"

# 코스 개수 체크
CONTENT_DIR="app/content"
BEFORE_COURSE=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')

# 가이드 개수 체크
GUIDE_DIR="app/content/guides"
mkdir -p "$GUIDE_DIR"
BEFORE_GUIDE=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')

print_info "1-1. 골프장 코스 컨텐츠 생성 중..."
python3 script/course_generator.py

print_info "1-2. 골프 가이드 컨텐츠 생성 중..."
# 한 번에 5개의 새로운 주제(파일 10개)를 생성하도록 제한 (API 관리용)
python3 script/guide_generator.py 5

AFTER_COURSE=$(find "$CONTENT_DIR" -maxdepth 1 -name "*.md" | wc -l | tr -d ' ')
AFTER_GUIDE=$(find "$GUIDE_DIR" -name "*.md" | wc -l | tr -d ' ')

NEW_COURSE=$(( AFTER_COURSE - BEFORE_COURSE ))
NEW_GUIDE=$(( AFTER_GUIDE - BEFORE_GUIDE ))

print_ok "컨텐츠 생성 완료!"
print_info "신규 코스: +${NEW_COURSE}개 (총 ${AFTER_COURSE}개)"
print_info "신규 가이드: +${NEW_GUIDE}개 (총 ${AFTER_GUIDE}개)"

# ── STEP 2: 이미지 수집 및 최적화 ────────────
print_step "STEP 2 / 6  |  이미지 수집 및 최적화"

MISSING=0
IMAGES_DIR="app/static/images"

if grep -q "GOOGLE_PLACES_API_KEY" .env; then
    # 이미지 없는 코스 확인
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
        print_ok "모든 코스 이미지 존재"
    fi
else
    print_warn "GOOGLE_PLACES_API_KEY 없음 → 이미지 수집 건너뜀"
fi

print_info "이미지 규격 검사 및 최적화 실행..."
python3 script/optimize_images.py
print_ok "이미지 처리 완료"

# ── STEP 3: 데이터 빌드 및 GCS 동기화 ───────
print_step "STEP 3 / 6  |  데이터 빌드 및 클라우드 스토리지 동기화"

print_info "JSON 및 Sitemap 갱신 중..."
python3 script/build_data.py
print_ok "데이터 빌드 완료"

if command -v gsutil &>/dev/null; then
    print_info "GCS 버킷으로 이미지 동기화 중..."
    gsutil -m rsync -r app/static/images gs://ok-project-assets/okcaddie
    print_ok "GCS 업로드 완료"
else
    print_warn "gsutil 없음 → GCS 동기화 건너뜀"
fi

# ── STEP 4: Git Push ───────────────────────
print_step "STEP 4 / 6  |  GitHub Push"

GIT_STATUS=$(git status --porcelain)
if [ -z "$GIT_STATUS" ]; then
    print_warn "변경 없음 → Git Push 건너뜀"
else
    git add .
    git commit -m "$COMMIT_MSG"
    git push origin main
    print_ok "GitHub push 완료"
fi

# ── STEP 5: Cloud Build & Cloud Run ───────
print_step "STEP 5 / 6  |  Cloud Build & Cloud Run 배포"
print_info "Google Cloud로 소스 전송 및 빌드 시작..."
gcloud builds submit
print_ok "Cloud Run 배포 완료"

# ── STEP 6: 완료 요약 ──────────────────────
print_step "STEP 6 / 6  |  완료 요약"

ELAPSED=$(( SECONDS - START_TIME ))
echo ""
echo -e "${BOLD}${GREEN}  🎉 전체 파이프라인 완료!${NC}"
echo ""
echo -e "  ⏱️  총 소요 시간  : $(( ELAPSED / 60 ))분 $(( ELAPSED % 60 ))초"
echo -e "  📄 신규 코스     : +${NEW_COURSE}개"
echo -e "  📖 신규 가이드   : +${NEW_GUIDE}개"
echo -e "  🖼️  처리된 이미지 : ${MISSING}개"
echo -e "  🌐 라이브 주소   : https://okcaddie.net"
echo ""

# Mac 사용자 알림 (선택사항)
if [[ "$OSTYPE" == "darwin"* ]]; then
    osascript -e 'display notification "배포가 완료되었습니다! 🎉" with title "OKCaddie Pipeline"' 2>/dev/null || true
fi
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""