# Electricity Group 2 – roles and GitHub accounts

Fill in the GitHub username of each member, then add them under **Settings → Collaborators**.
Roles were taken from the group role table; confirm them before the first push.

| Role | Member | Student ID | GitHub username | Main folders / duties |
|---|---|---|---|---|
| Project Manager | Tyrese Jonathan Mapangisana | N02534462L | @_______ | Issues board, milestones, PR approvals, supervisor reports, README/docs |
| Software Engineer | Hope Munashe Chibare | N02532738H | @_______ | `launch/`, `config/bridge.yaml`, package structure, code review |
| Systems Engineer | Tawananyasha Tarugarira | N02532657D | @_______ | `models/`, `tools/generate_models.py`, `docs/physical_droid.md`, hardware build |
| Network Engineer | Precious R Magaya | N02529749P | @_______ | LoRa/WiFi link simulation, message format, POTRAZ rules |
| Programmer 1 | *unassigned* | | @_______ | to be agreed (suggest: navigation/docking helpers for the later autonomy phase) |
| Programmer 2 | Tinevimbo Chikaka | N02534499J | @_______ | `scripts/brush_control.py`, `scripts/cleaning_monitor.py` |
| Test Programmer | Patience Mafira | N02529263K | @_______ | `tools/check_repo.py`, `test/`, bug reports |
| Database Administrator | Ashton Ndlovu | N02532750L | @_______ | SQLite reports/logs schema, panel inventory |
| AI/ML Engineer | Bernard J Kadenhe | N01531833Y | @_______ | Dust/crack dataset and inspection model |
| Chief Security Officer | *unassigned* | | @_______ | Authenticated commands, keys out of source, privacy |

## Working agreement
- `main` is protected: changes arrive by pull request, reviewed by the Software Engineer (code) or Systems Engineer (models).
- Branches: `feature/<role>-<topic>`. Commit messages: short, present tense.
- Regenerate models with `python3 tools/generate_models.py` instead of hand-editing generated SDF.
- Run `python3 tools/check_repo.py` before every pull request.
