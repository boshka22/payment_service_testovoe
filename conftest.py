"""Конфигурация pytest — добавляет корень проекта в sys.path."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
