# 검증 기록

## E1 환경과 소스
2026-10-20: 빈 작업 폴더. Python/Node는 Codex 번들 런타임 존재. PATH python은 WindowsApps alias이므로 사용하지 않음. 사용자 Start Menu에 OpenCodex, Blender, Ollama, Discord 바로가기 확인(설치/실행 여부 증거와 구분).
관련 스킬 settings/model-routing/project-records/verification/interface-craft/tdd 및 로컬 선택 규칙 읽음. 제공된 구독 비용보호 증거 파일의 만료 여부는 guarded launcher가 실행 시 판단. 인증 파일 내용은 읽지 않음.

## 외부 호출 원장
Anthropic 시도 2/2 (첫 sandbox preflight 실패: model_dispatch_attempted=false; 두 번째 require_escalated 성공). 실제 응답 1, run 490dfec2176146208969f9cba9290191 / thread 01a1580d-8d89-7911-a25f-288a03f45eea. requested anthropic/claude-opus-5-5 medium, reported null. terminal completed, subscription guard true, 추가 호출 block false. 원본 reviews/architect-live. xAI 0/2 최종 1 예약, Google 0/1. sandbox 내부 ocx 상태는 네트워크 제한으로 unavailable이었고, 호스트 읽기에서는 10100 포트 healthy, 2.88.0 확인. 서비스 변경 없음.

## E2 설계 반영
첫 CPU null, 고정 디스크, 64-bit ctypes 선언, 단일 샘플러, 프로세스 15초·캐시 30초, 깨진 캐시 이전 값 유지 + 오류 표시, 2 MiB 읽기 상한 채택. GPU/트레이/자동시작/모델 호출 제외. 브라우저 저장이므로 서버 할 일 파일 교체 제안은 적용 대상 없음.

## E3 자동 검사 (2026-10-20 15:59 KST 부근)
작업 디렉터리는 본 프로젝트. Python: `C:\Users\Desktop\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -X utf8 -B -m unittest discover -s tests -v` -> exit 0, 11 passed. Node 동일 번들 `node.exe --test tests/ui.test.cjs` -> exit 0, 4 passed. `node.exe --check web/app.js` exit 0.
최초 캐시/API/프런트 로직 테스트는 각각 미구현 import로 실패 후 구현. 캐시 검사는 먼저 4개 값/날짜 검사가 통과; TEMP ACL 오류 3개는 프로젝트 .scratch를 프로세스 TEMP/TMP로 지정해 해결. HTTP socket WinError10013은 sandbox 네트워크 제한으로, 호스트 권한에서 동일 검사를 실행해 통과. 테스트 약화 없음. raw: artifacts/python-tests.txt, artifacts/node-tests.txt.

## E4 실제 Windows 메모리/데이터
실행 중 GET /api/status를 3초 간격 5회 관찰: working set min 24.88671875 / max 24.91796875 / median 24.890625 MiB. 최초 목표 40 MiB 이하 충족. 당시 시스템 RAM total 34,046,746,624 bytes, used 17,159,131,136, CPU 3.1%, 시스템 디스크 C: total 999,046,508,544/free 561,508,081,664. 원본 .scratch/measurement.json. 브라우저 추가 메모리는 측정하지 않았으며 총합 절감 수치는 주장하지 않음. 정적 웹 자원 합계 약 42 KiB. 초기 이력 48개, 상한 60 구현.

## E5 사용자 흐름·화면
실제 CUA IAB http://127.0.0.1:8765/ 연결. PC 실제값, Codex 프로세스, OpenCodex health, 네 AI 캐시 사용량/오래됨 배지 확인.
UI: 검증용 연간 120,000 KRW 구독 추가 -> 월 10,000, 다음날 갱신 표시 -> reload 후 유지 -> 검증용 구독 삭제/저장 확인. 집중 목표와 할 일 추가 -> reload 유지, 할 일 완료/삭제, 테스트 목표 비움. javascript: 바로가기 입력 -> 오류 표시, https://example.com 등록 -> reload 후 href 유지 -> 테스트 링크 삭제. 테스트 데이터 최종 정리.
Desktop 1280x900 및 mobile 390x844 검증, DOM clientWidth=scrollWidth(각각 1265/375, 스크롤바 제외), 가로 넘침 없음. console error/warn 빈 목록. 폰트/카드/입력/모달 시각 점검. artifacts/dashboard-desktop.png full-page 스크린샷. 임시 viewport 초기화, 결과 탭 markDeliverable.

## E6 실행 수명
launcher start --no-browser 재실행 -> PID 9484 재사용. stop -> health 연결 없음. start -> PID 39412로 재실행. 각 exit0, artifacts/lifecycle.json. 최신 sampler wake 반영 후 재연결 정상. Open/Stop cmd는 이 PC의 기존 Python을 호출하며 전역 설치/정책 변경/자동시작 없음.

## E7 최종 검토 예약
xAI 시도 1/2: exec_command auto-review 단계에서 거절되어 helper/model dispatch 없음. stated reason: 전체 코드·검증·로컬 경로 payload의 외부 Grok/xAI 전송에 명시적 사용자 승인이 필요. 전송하지 않았으며 우회/다른 transport 사용 없음. 원본 reviews/challenger-input.txt 보존. 개인 경로·계정 메타데이터·인증 자료를 제외한 reviews/challenger-redacted.txt를 로컬 준비. 새 소스/테스트 결과를 Grok(xAI)에 보내도 되는지 사용자 명시적 승인 질문 대기. 실제 Grok 응답 0; 최종 검토 미완료. 기존 Claude 설계 참여와 로컬 검증은 유효.

## E8 범위 변경과 승인
사용자가 Grok(xAI)로 새 코드/테스트 결과 전송을 명시 승인. 이후 디자인 불만, VRAM 추가 요청 및 밝은 아이보리/큰 글씨/정돈된 개인 작업실 방향을 선택. GPU·ComfyUI 연동에는 comfyui 스킬 사용. 기존 Desktop helper로 온라인8188/ComfyUI0.42.1/RTX5070Ti 확인, 큐0/0. 서비스·모델·작업 변경 없음.
설치 스킬의 관련 항목은 interface-craft 및 Figma 관련 스킬. 'Awesome Design' 이름의 로컬 스킬 없음. interface-craft가 가리킨 Impeccable 원칙을 참고(설치하지 않음): https://github.com/pbakaus/impeccable . NVML API/struct 공식 근거: https://docs.nvidia.com/deploy/nvml-api/latest/api/group__nvmlDeviceQueries.html 및 https://docs.nvidia.com/deploy/nvml-api/latest/api/structnvmlMemory__v2__t.html .

## E9 GPU 포함 버전 검증
Python `-X utf8 -B -m unittest discover -s tests -v` exit0, 15 passed; Node `--test tests/ui.test.cjs` exit0, 4 passed. artifacts/python-tests-v2.txt/node-tests-v2.txt. 추가 모듈 테스트는 미구현 import 실패 후 구현/통과. missing NVML/offline Comfy/잘못된 큐를 0으로 위장하지 않는 경계와 프롬프트 비노출 확인.
artifacts/measurement-v2.json: 3초 간격5회 수집기 working set 46.4258~46.4570 MiB. GPU 미포함 이전25MiB와 같은 지표지만 기능이 달라 성능 향상 비교 아님. 초기40MiB 목표는 미달(false). 별도 진단 프로세스 base14.75MiB → NVML init37.31MiB, 개별조회 추가는0.06MiB, 드라이버 초기화가 약22MiB 증가 원인. 브라우저 메모리는 미측정.
NVML v2 total17,094,934,528 bytes(약16,303.44MiB), nvidia-smi total16,303MiB와2MiB미만 차이. used3,446,079,488 bytes vs nvidia-smi3,287MiB로 일치하는 범위. free13,325,893,632 bytes, reserved322,961,408 bytes. ComfyUI0.42.1 online, running0/pending0. 실제 생성/과부하 상황은 실행하지 않음.

## E10 재디자인 화면
1440x1000 desktop DOM clientWidth/scrollWidth1425 동일, VRAM3.2/15.9GiB, Comfy0/0 실제 렌더. 390x844 mobile DOM375/375, main 가로넘침0. 모바일 구독 모달 width341/scrollWidth324로 넘침없음. 모달 체크박스의 잘못된 고정폭을 시각검사 후 수정. 이전 localStorage 구독/바로가기 유지 확인. artifacts/dashboard-light-desktop.png / dashboard-light-mobile.png. 사용자 선택에 맞춘 아이보리+올리브/테라코타, 4개AI 일렬, 첫화면Comfy/VRAM, 얇은구분선으로 개정. 최종검토는 이 코드/증거 기준으로 진행.

## E11 실제 Grok 최종 검토
사용자 전송 명시 승인 후 reviews/challenger-v2-approved.txt 전송. xAI 시도2/2(거절 시도 포함), 실제응답1. run cdadf08a6d4849648dfdc896116eb36a, thread01a15828-b8a1-7d80-a7e3-0b9640fb202c, requested xai/grok-4.7 low/reported null(신원 unattested). terminal completed, response/guard succeeded, block false, quota 요청없음. 원본 reviews/challenger-v2/response.md 및run.json.
요구 적합성 충족/차단 결함 없음 판정. 낮은 지적: (1) 종료 PID재사용 위험: 실제보완. (2) v2used가 예약 메모리를 제외한다는 사실은 맞으나 nvidia-smi보다 낮다는 추정은 raw 측정 used3286.44MiB/nvidia-smi3287MiB와 맞지 않아 점유량 의미를 바꾸지 않음. 대신 시스템 예약량을 화면/툴팁으로 별도표시. (3) 미확인 막대와uptime을 0처럼 그리는 처리: 비워진 점선/미확인으로 보완.

## E12 검토 후 로컬 수정과 최종 확인
검토 후 수정은 launcher.py, web/app.js, web/style.css. peer가 이 수정본을 다시 검토한 것은 아님. launcher는 시작한 실제 자식이 살아 있는 상태에서WindowsGetProcessTimes의 생성 FILETIME을 기록하고, stop시 같은 열린 핸들의 생성시각·실행경로·기존APP_ID/PID를 함께 확인. 실제 instance.created_ticks+1 테스트 -> stop exit1, 원래서버 생존; 원본복구 -> stop exit0/health없음 ->start정상. artifacts/lifecycle-creation-regression.json.
수정 후Python15/Node4 통과, JS구문검사exit0(artifacts/*-tests-final.txt). NVML포함 마지막지속관찰46.67MiB, history60 확인. 최종소스해시는 artifacts/source-manifest-v2.json 갱신. GPU 및ComfyUI실행 상태·예약량 표시 재확인 후 브라우저탭을 유지한다.
최종 브라우저 재확인: GPU 할당3.2/15.9GiB, 시스템예약0.3GiB/여유12.4GiB 툴팁 및 ComfyUI캡션, 작업실링크8188, client/scrollWidth1425동일. artifacts/dashboard-final.png 저장. 임시viewport초기화 및 markDeliverable 완료. 수집기 실행중, 전역자동시작없음.

## V3 원장 시작
기존 완료 V2와 구분. 새 범위 사용자 승인, 용인기본+위치추적 명시 요청. 읽기전용 sandbox이므로 승인된 프로젝트 수정은 require_escalated 경로 사용. 이전 파일 .scratch/pre-weather-news-v3 복사. 설계 packet reviews/v3-architect-input.txt. Anthropic 시도1/2 예약, xAI0/2 최종1예약, Google0/1불필요. 기존 plan 단계 실제 RSS200확인(HF882/260416bytes, GeekNews50/45425bytes, GitHubChangelog10/38572bytes) 재사용.

## V3 E13 설계 실제 참여
Anthropic1/2시도, 실제응답1. run0ed3421506c44ed1a8035a6144e67ff6 / thread01a1586d-f489-7a53-b615-e1d8f6948899, requested anthropic/claude-opus-5-5 medium, reportednull(unattested), guardtrue/terminalcompleted/blockfalse. reviews/v3-architect/response.md. 채택: 별도공개스레드, 네트워크중lock없음, 세대/칸식별, 탭owner90초임대, 기본용인만디스크, RSS/Atom파싱/시각, 원자적캐시, 저장키보존. GPS직접좌표/현재날씨는RAM만, 숨김owner해제/세대증가.
## V3 E14 구현·테스트
28Python +9Node 통과, JS구문통과. 동일번들Python/Node, cwd본프로젝트, TEMP/TMP=.scratch, 호스트권한. 명령은 README, raw artifacts/v3-python-tests.txt 및v3-node-tests.txt. 좌표±90/±180·초과/bool/NaN, TTL전무호출/오류성공시각유지/재시작/위치A요청중B전환/좌표비저장/다른탭리셋거부/임대만료/잘못된POSTOrigin/본문512초과/순수JSON, RSS+Atom+중복/날짜/HTTPS링크/실제XMLDTD거부/CDATA예제허용, 외부작업gate중PCAPI1초이내응답. Node추적중지/재개/이전callback무시/흔들림동일위치무전송/미지원/동기오류/구독저장시focus/tasks/links/unknown값보존.
첫public_data/위치API는 미구현 실패→구현통과. 보존헬퍼/동기위치예외/동일위치이벤트 억제는 각각 실패→수정통과. 최초파일작성 JSON인용문오류는 로컬쓰기수정(모델추가호출없음). 실제RSS에서2개독립문제: GitHub기사CDATA내doctype를문서DTD로오인 -> 구조적Expat DTD거부로수정, 실제GitHub10건통과. RFC822 Tue/Thu의T를ISO판별에사용해날짜None -> 테스트실패재현후ISO시도/RFCfallback로수정, HF게시1일/4일정상렌더. 같은원인재시도반복없음.
## V3 E15 실제 데이터와 제한
artifacts/v3-live-measurement.json: 활성3초간격5회52.296875~52.33203125MiB(기능구성이다르므로이전47MiB와절감비교아님), history60/Comfy온라인. 실제용인17.2도/최고19.9/최저10.1/강수25, OpenMeteo응답기준. 소스github10/HF12/GeekNews12, 모두errorfalse. 본문/이미지/개인메타보관없음. 브라우저에서현재위치사용시위치획득실패→용인복귀문구/실제데이터유지확인. 정밀위치실제전송/성공이동은관찰못함. Node합성좌표및서버경계로성공논리검증; OS/브라우저위치환경한계명시. 시스템설정변경없음.
## V3 E16 사용자 흐름
실제IAB1440화면: 상단용인+작은PC, Comfy/GPU단일패널, AI플랜·링크, 뉴스8개. GitHub/HF필터각8건표시및원문href확인, HF날짜1/4일전확인. 390x844 DOM client/scroll375동일, focus/tasks/links패널노드없음. 구독기존4개그대로저장→reload→Pro monthly/Plus monthly/Google AI Plus유지. 상세토글true시앱3행, 다시접힘. 원위치데이터/권한별실패는위E15구분. 사용자저장값/다른앱미변경.
## V3 E17 최종검토 dispatch
xAI시도1/2예약, 기존프로젝트새소스/테스트Grok전송승인재사용. 개인경로/계정/실위치/읽은기사내역제외한packet생성. 실제응답전까지최종단계미완료.

## V3 E18 최종 검토와 검토 후 확인
xAI 시도 1/2, 실제 응답 1. run c097e18033224aa680a46801cbc81db3 / thread 01a15882-6655-77e1-a1b4-776ca5357746. requested xai/grok-4.7 low, reported null(신원 unattested). terminal completed, response/guard succeeded, block false. reviews/v3-challenger/response.md 및 run.json. Claude 설계와 Grok 독립 검토 모두 실제 응답으로 참여했으며 Flash는 불필요했다.
검토 결과는 차단 결함 없음/수용 기준 충족. 추가 지적: HTTPException(IncompleteRead 등)/RecursionError가 공개 작업자를 종료할 수 있음(중간), 큰 JSON 정수의 OverflowError(낮음), 허용 호스트의 비표준 HTTPS 포트 리디렉션(낮음). 조정자가 실패 회귀를 재현한 뒤 public_data.py/server.py 및 관련 테스트를 보완했다. 네트워크·파싱 예외 시 마지막 성공값/시각을 보존하고 다음 조회에서 복구, 큰 정수는 잘못된 좌표로 거부, 리디렉션 포트는 기본/443만 허용. Grok이 이 수정본을 다시 검토한 것은 아니다.
수정 후 최종 검사: Python unittest 30 통과(exit0), Node 9 통과(exit0), web/app.js 구문 검사 exit0. raw artifacts/v3-python-tests-final.txt 및 v3-node-tests-final.txt. 기존 검사 이후 변경된 예외·입력 경계에 맞춰 검증했으며 추가 모델 호출은 없다. artifacts/source-manifest-v3.json은 최종 소스와 테스트 해시로 갱신.
최종 수집기 재실행 후 브라우저에서 용인 날씨/뉴스 8개/상세 접힘 확인, desktop clientWidth/scrollWidth 1425/1425. artifacts/v3-dashboard-final.png 저장, 임시 viewport 초기화, 결과 탭 markDeliverable. 현재 수집기 실행 중. 공개 디스크 캐시는 version/default_weather/feeds만 포함하고 현재 좌표/owner는 없다. 자원 실측은 E15(약53MiB, 브라우저 별도), 실제 브라우저 위치 획득 실패와 성공 미확인은 E15 그대로 유지한다. 최종 V3 요청 범위 구현·검증·검토 완료, 네이티브 위치의 성공 이동은 합성 테스트와 구분한다.

## V4 E19 UI/UX 정돈
원본 .scratch/pre-ui-refinement-v4, 범위 web/index.html/web/style.css/web/app.js. interface-craft 적용. 표시에 국한한 개선이라 multi-ai auto→solo; 신규 외부 모델 응답 없음. 이전 V3의 Claude/Grok 검토를 이번 수정본의 재검토라고 주장하지 않음. CSS/HTML/렌더링·초점만 수정, 서버/수집/위치 프로토콜/구독 저장 계약 유지. 초기 대용량 명령은 Windows 명령줄 길이 제한으로 실행 전 실패했고 명령을 분리해 적용했으며 추가 모델 호출 없음.
최종 Node --check web/app.js exit0, Node --test tests/ui.test.cjs tests/location.test.cjs exit0/9 passed. raw artifacts/v4-syntax.txt / v4-regressions.txt. 백엔드 변경이 없어 V3 Python 30개 결과는 이전 증거로 유지하며 새 실행으로 집계하지 않음.
실제 IAB 확인: 1440x1000 및 1440x1140 데스크톱 가로 client/scroll1425동일, 768x1024 753/753, 390x844 375/375, 320x800 305/305. 좁은 폭의 AI행/뉴스필터/날씨/섹션 헤딩 넘침 검사도 빈 목록. 태블릿은 단일 열, 4개 AI의 플랜/사용량/캐시 시각 유지, ComfyUI와 VRAM 실제 값/용인 날씨/뉴스 8개 유지. 최초 2x2 AI의 빈 공간을 행으로 정리한 뒤 재확인.
모바일 HF 필터 aria-pressed true/8개 모두 huggingface.co HTTPS, 전체 복귀 확인. 필터에서 Tab → 첫 뉴스 링크, 기사 전체에 solid 포커스, 메타 영역의 DOM hit가 news-link이므로 행 단위 클릭 범위 확인. 상세 버튼 열기 → summary 초점/aria-expanded true/실행도구3행; Enter로 접기. 위치 모달 열기/Escape닫기(위치 권한 재요청/설정 변경 없음). 구독 모달 4개 기존 값 유지, 이름/플랜/금액/주기/갱신일 입력 노출, 취소로 닫기. 모바일 date input242px, dialog client/scroll339동일, 저장 버튼 bottom769.36 < viewport844. 목록만 내부 스크롤, 저장·취소 상시 노출. 편집값 저장이나 기존 구독 삭제는 수행하지 않음.
콘솔 error/warn 빈 목록. artifacts/v4-mobile-news.png / v4-mobile-settings.png / v4-dashboard-final.png. 최종 화면은 1440x1140에서 저장, 상세 접힘/뉴스8/AI4. viewport 초기화와 탭 markDeliverable 완료. 검토 가능한 범위 diff artifacts/v4-ui.diff, 최종 해시 source-manifest-v4.json. 새 패키지·폰트·상주 프로세스 없음; 브라우저 RAM 개선 수치는 측정/주장하지 않음.
