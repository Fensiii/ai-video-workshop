# Skill sources

All skills were copied from these upstream repositories (shallow clone, commit shown). To update one, re-clone it and re-copy the same paths, then re-apply the local changes listed below.

| Upstream | Commit | Installed as |
|---|---|---|
| digitalsamba/claude-code-video-toolkit | 959e0fc | `.claude/skills/{acestep,elevenlabs,ffmpeg,ideogram4,ltx2,moviepy,playwright-recording,qwen-edit,remotion,runpod}`; scripts in `.claude/video-toolkit/` |
| remotion-dev/remotion (`packages/skills/skills`) | 359df61 | `.claude/skills/remotion-*` |
| Vincentwei1021/video-talkcraft | a7c29ed | `.claude/skills/video-talkcraft` (whole repo) |
| Vincentwei1021/video-shotcraft | 310330c | `.claude/skills/video-shotcraft` (whole repo) |
| heygen-com/hyperframes (`skills/`) | 6f0e1f1 | 21 published skills (`hyperframes*`, `general-video`, `pr-to-video`, ...) |
| Melvynx/video-agent-skills (`skills/`) | b2b028b | `editing`, `short-editing`, `broll`, `clips`, `vox`, `publish`, ... |
| scrollmark/social-skills | f5b8bc5 | repo in `.claude/vendor/social-skills/`, symlinked as `social-skills--*` |
| iart-ai/{map-animation,text-message-video,data-animation,explainer-video,manim,tiktok-video}-skills | 390ca98 / 3a800e1 / 8ce2709 / 3e2d411 / a15833c / 2a77533 | one dir per skill, repo `scripts/` copied into each |
| AgriciDaniel/claude-shorts | a369fad | `.claude/skills/shorts` |
| rediumvex/viral-hooks-skill | e26b339 | `.claude/skills/viral-hooks` |
| yanhua1010/self-media-content-workflow (`skills/`) | eaa895a | `self-media-*`; repo scripts in `.claude/vendor/self-media-content-workflow/` |
| larry-xue/lianyun-video-skill (`skills/`) | 6ef6aab | `lianyun-video*` |
| atian-create/lingzao-skill | 1727b3a | repo in `.claude/vendor/lingzao-skill/`, symlinked as `lingzao` + its `skills/*` |
| chubbyguan/chubbyskills | d066d76 | repo in `.claude/vendor/chubbyskills/`, symlinked per skill |
| ballbasecn-star/claude-skill-douyin | 9a618f7 | `.claude/skills/douyin` |
| Fangyuan025/tiktok-video-skill | 9c3122d | `.claude/skills/tiktok-video` |

## Local changes

- Toolkit skills: `tools/` and `docker/` paths rewritten to `.claude/video-toolkit/...`; `remotion` points to `remotion-best-practices` instead of `remotion-official`.
- `video-agent-skills/studio-setup` renamed to `video-studio-setup` (clashed with social-skills), with its references updated.
- `hyperframes` description narrowed so it no longer claims every video request; Remotion is the default (see CLAUDE.md).
- social-skills: `editor-*` (need a running Scrollmark editor), `studio-setup` and `trend-radar` are not linked as skills; `audio-acquisition`, `media-acquisition` and `video-production` point at the unlinked `studio-setup` files by path.
- Not installed: toolkit `frontend-design` and `remotion-official`, repo-internal maintainer skills (remotion `.agents/`, hyperframes `.claude/` and `.agents/`, hyperframes `registry/blocks`), README-only images in video-shotcraft.
