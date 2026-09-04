# 커스텀 fork 안내

[YeeDochi/Claudlet](https://github.com/YeeDochi/Claudlet) 의 fork 입니다.
`custom` 브랜치가 이 fork 의 기준 브랜치이고, 업스트림에 없는 3가지가 들어 있습니다.

| | 내용 |
|---|---|
| 1 | **픽셀 깨짐 수정** — 아트픽셀을 정수 픽셀 그리드에 맞춰 렌더. 회전 프레임만 안티에일리어싱을 켜 계단 현상 제거 |
| 2 | **클릭 시 내 프로젝트 창으로 포커스** — JetBrains IDE 는 열어둔 프로젝트 전부가 한 프로세스라 pid 만으로는 창을 못 고른다. 창 제목의 프로젝트로 골라서 올린다 |
| 3 | **펫 하단에 프로젝트명 고정 표시** — 프로젝트별 고정 색상도 함께 |

## 설치

```bash
pipx install --force "git+https://github.com/Rio-Kyeong/Claudlet@custom"
claudlet-install
```

두 번째 줄이 훅과 `/claudlet` 스킬을 등록합니다. 그다음 Claude Code 세션을 새로
시작하면 세션마다 펫이 자동으로 붙습니다.

다른 PC·다른 계정도 위 두 줄이면 끝입니다. 설정 파일을 옮길 필요는 없습니다.

## 업데이트

**`pipx install --force claudlet` 을 쓰지 마세요.** PyPI 릴리스를 끌어와 위 3가지를
전부 지웁니다. `pipx upgrade` 도 마찬가지입니다. 대신:

```bash
claudlet-sync
```

fork 를 클론해 업스트림 최신 릴리스를 `custom` 에 merge → push → 그 브랜치에서
재설치 → 훅 재설치 → 펫 재부착까지 한 번에 합니다. merge 가 충돌하면 (업스트림이
커스터마이즈와 같은 줄을 고친 경우) **아무것도 설치하지 않고 멈춥니다.** 그때는
사람이 직접 합쳐야 합니다.

옵션: `--develop` (릴리스 대신 upstream/develop 머지), `--no-merge` (머지 없이
재설치만), `--no-restart` (펫 재부착 생략).

## 설정

`~/.config/claudlet/config.json` (Windows: `%USERPROFILE%\.config\claudlet\config.json`)

```json
{
  "palette": "project",
  "show_project": true,
  "project_palettes": { "my-project": "#2FA88C" }
}
```

- `palette: "project"` — 프로젝트 이름 해시로 색 결정. 같은 프로젝트면 항상 같은 색
- `show_project: false` — 펫 하단 이름 표시 끄기
- `project_palettes` — 두 프로젝트 색이 겹칠 때 직접 지정 (색상 12 × 톤 3 = 36가지라
  프로젝트가 많으면 겹칠 수 있음)

나머지 설정은 [docs/configuration.ko.md](docs/configuration.ko.md) 와 동일합니다.

## 확인

```bash
claudlet-version
pipx list --json    # package_or_url 이 git+...@custom 이어야 함
```

## 브랜치

| 브랜치 | 용도 |
|---|---|
| `custom` | **설치 대상.** 3가지 커스터마이즈 + 업스트림 머지 |
| `fix/pixel-grid-crispness` | 1번을 업스트림에 올린 PR ([#5](https://github.com/YeeDochi/Claudlet/pull/5)) |
| `develop`, `master` | 업스트림 미러 |

1번은 업스트림 PR 로 올려둔 상태라, 병합되면 `custom` 에서 해당 커밋을 빼도 됩니다.
2·3번은 이 fork 전용입니다.
