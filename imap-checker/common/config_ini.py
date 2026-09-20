#!/usr/bin/env python3
"""Đọc/ghi ``context/config.ini`` — dùng chung cho UI lẫn script."""
import configparser

from common.paths import CONFIG_PATH


def load_ini():
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_PATH, encoding="utf-8")
    return cfg


def save_ini(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        cfg.write(f)


def job_sections(cfg):
    """Chỉ trả về section job thật — bỏ section chú thích/hướng dẫn không có
    key chuẩn (``recent_minutes``)."""
    return [s for s in cfg.sections() if "recent_minutes" in cfg[s]]
