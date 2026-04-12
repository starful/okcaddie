#!/bin/bash
# ⛳ OKCaddie 자동 배포 파이프라인 (Google Places 이미지 수집 및 GCS 동기화 포함)
# 실행: ./deploy.sh

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
COMMIT_MSG="update: auto-generated contents & UI $(date '+%Y-%m-%d %H:%M')"

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

grep -q "GOOGLE_PLACES_API_KEY" .env && SKIP_IMAGES=false || { print_warn "GOOGLE_PLACES_API_KEY 없음 → 이미지 수집 건너뜁니다"; SKIP_IMAGES=true; }
grep -q "GEMINI_API_KEY" .env || { print_err "GEMINI_API_KEY 없음"; exit 1; }
print_ok "API 키 확인"

command -v python3 &>/dev/null || { print_err "python3 없음"; exit 1; }
command -v gcloud  &>/dev/null || { print_err "gcloud 없음"; exit 1; }
command -v git     &>/dev/null || { print_err "git 없음"; exit 1; }
command -v gsutil  &>/dev/null || { print_err "gsutil 없음 (Google Cloud SDK 필요)"; exit 1; }

CSV_PATH="script/csv/courses.csv"
[ ! -f "$CSV_PATH" ] && { print_err "CSV 없음: $CSV_PATH"; exit 1; }
CSV_COUNT=$(( $(wc -l < "$CSV_PATH") - 1 ))
print_ok "골프장 CSV: 총 ${CSV_COUNT}개"

# ── STEP 1: AI 컨텐츠 생성 ─────────────────
print_step "STEP 1 / 6  |  AI 컨텐츠 생성 (Gemini API)"

CONTENT_DIR="app/content"
BEFORE_COUNT=0
[ -d "$CONTENT_DIR" ] && BEFORE_COUNT=$(find "$CONTENT_DIR" -name "*.md" | wc -l | tr -d ' ')

python3 script/course_generator.py

AFTER_COUNT=$(find "$CONTENT_DIR" -name "*.md" | wc -l | tr -d ' ')
NEW_COUNT=$(( AFTER_COUNT - BEFORE_COUNT ))
print_ok "컨텐츠 생성 완료! (총 ${AFTER_COUNT}개, 신규 +${NEW_COUNT}개)"

# ── STEP 2: 이미지 수집 및 최적화 ────────────
print_step "STEP 2 / 6  |  이미지 수집 및 최적화"

MISSING=0

if [ "$SKIP_IMAGES" = true ]; then
    print_warn "건너뜀"
else
    IMAGES_DIR="app/static/images"
    if [ -d "$CONTENT_DIR" ]; then
        for md_file in "$CONTENT_DIR"/*_en.md; do
            [ -f "$md_file" ] || continue
            base=$(basename "$md_file" _en.md)
            if [ ! -f "${IMAGES_DIR}/${base}.jpg" ]; then
                MISSING=$((MISSING + 1))
            fi
        done
    fi

    if [ "$MISSING" -eq 0 ]; then
        print_ok "모든 이미지 존재 → 다운로드 스킵"
    else
        print_info "이미지 없는 골프장: ${MISSING}개 → 수집 시작"
        python3 script/fetch_images.py
        print_ok "이미지 수집 완료"
    fi
    
    # 💡 수집 여부와 상관없이 수동 추가 이미지를 위해 최적화는 항상 실행
    print_info "이미지 규격 검사 및 최적화 중..."
    python3 script/optimize_images.py
    print_ok "이미지 최적화 완료"
fi

if [ "$NEW_COUNT" -eq 0 ] && [ "$MISSING" -eq 0 ]; then
    print_warn "새로 생성된 컨텐츠나 이미지가 없습니다. (UI 업데이트만 배포 가능)"
    echo ""
    read -p "  그래도 계속 배포하시겠습니까? (y/N): " -n 1 -r
    echo ""
    [[ ! $REPLY =~ ^[Yy]$ ]] && { print_info "취소"; exit 0; }
fi

# ── STEP 3: JSON 빌드 및 GCS 동기화 (핵심 추가) ─
print_step "STEP 3 / 6  |  데이터 빌드 및 클라우드 스토리지 동기화"

print_info "JSON 및 Sitemap 갱신 중..."
python3 script/build_data.py
print_ok "데이터 빌드 완료"

if [ -d "app/static/images" ]; then
    print_info "GCS 버킷으로 이미지 동기화 중 (rsync)..."
    # 삭제 옵션(-d)은 위험할 수 있으니 제외하거나 유지 선택 (현재 안전하게 -m 병렬 업로드만 사용)
    gsutil -m rsync app/static/images gs://ok-project-assets/okcaddie
    print_ok "GCS 이미지 업로드 완료"
fi

# ── STEP 4: Git Push ───────────────────────
print_step "STEP 4 / 6  |  GitHub Push"

GIT_STATUS=$(git status --porcelain)
if [ -z "$GIT_STATUS" ]; then
    print_warn "변경 없음 → Git Push 건너뜀"
else
    print_info "변경된 파일: $(echo "$GIT_STATUS" | wc -l | tr -d ' ')개"
    git add .
    git commit -m "$COMMIT_MSG"
    git push origin main
    print_ok "GitHub push 완료"
fi

# ── STEP 5: Cloud Build & Cloud Run ───────
print_step "STEP 5 / 6  |  Cloud Build & Cloud Run 배포"
print_info "약 2~4분 소요됩니다..."
echo ""
gcloud builds submit
print_ok "Cloud Run 배포 완료"

# ── STEP 6: 완료 요약 ──────────────────────
print_step "STEP 6 / 6  |  완료 요약"

ELAPSED=$(( SECONDS - START_TIME ))
echo ""
echo -e "${BOLD}${GREEN}  🎉 전체 파이프라인 완료!${NC}"
echo ""
echo -e "  ⏱️  총 소요 시간  : $(( ELAPSED / 60 ))분 $(( ELAPSED % 60 ))초"
echo -e "  🖼️  수집된 이미지 : ${MISSING}개"
echo -e "  📄 전체 컨텐츠   : ${AFTER_COUNT}개 (신규 +${NEW_COUNT}개)"
echo -e "  🌐 라이브 사이트 : https://okcaddie.net"
echo ""

osascript -e 'display notification "배포가 완료되었습니다! 🎉" with title "OKCaddie 파이프라인"' 2>/dev/null || true
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""