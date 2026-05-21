# 古印度与印度史 vIndian

This directory is a v03-compatible source dataset for Indian and South Asian
history through 1990.

Current scope:

- Historical South Asia before 1947.
- Republic of India focus after 1947, with Pakistan/Bangladesh context only
  where directly tied to partition, war, or territorial integration.
- BCE years are negative integers and year 0 is omitted.
- Modern geography fields are approximations for indexing, not historical
  boundary claims.
- Princely-state rows imported from Rulers.org are candidate rows and should
  be upgraded with Imperial Gazetteer or official corroboration before being
  used for high-confidence map display.
- Epic, Puranic, dynastic-origin, and regional royal-chronicle traditions are
  stored separately in `mythological_timeline_vIndian.csv`. They may be played
  as a cultural timeline, but they must not generate historical polity yearly
  rows or actual-control map claims.

Regenerate yearly rows:

```bash
python3 scripts/generate_world_history_yearly.py --dataset vIndian
python3 scripts/validate_world_history_dataset.py --dataset vIndian
```
