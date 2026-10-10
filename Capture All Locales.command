#!/bin/zsh
set -eu
cd "${0:A:h}"
run="outputs/six-scenes-all-$(date +%Y%m%d-%H%M%S)-$$"
print 'Съёмка шести сцен для всех 14 локализаций.'
print 'Не управляйте тестовой игрой во время съёмки.'
print "Результаты: $PWD/$run"
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B Scripts/visual-qa/capture_all_locales.py capture --output "$run"
open "$run"
print 'Кадры сняты. Визуальная проверка выполняется отдельно; оригиналы сохранены.'
