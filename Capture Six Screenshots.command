#!/bin/zsh
set -euf

capture_root=${0:A:h}
cd "$capture_root"
capture_run="outputs/six-scenes-ru-$(date +%Y%m%d-%H%M%S)-$$"

PYTHONDONTWRITEBYTECODE=1 "$capture_root/.venv/bin/python" -B \
  Scripts/visual-qa/capture_six_scenes.py replay --output "$capture_run"

print 'Снято шесть JPEG. Проверь изображения перед использованием:'
print "$capture_root/$capture_run/jpeg"
/usr/bin/open "$capture_root/$capture_run/jpeg"
