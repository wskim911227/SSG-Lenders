# Git 자동 동기화

이 프로젝트의 원격 저장소는 https://github.com/wskim911227/SSG-Lenders.git 입니다.

코드 수정이 완료되면 반드시 아래를 수행하세요:

1. 관련 변경 파일만 `git add`
2. 변경 내용을 설명하는 커밋 메시지로 `git commit`
3. `git push origin main` (또는 현재 브랜치)

Agent 작업 종료 시 `.cursor/hooks/auto-push.sh` 훅이 변경사항을 자동 커밋/푸시합니다.
