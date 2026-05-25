"""Resumen del día — delegado al informe unificado de fichajes."""

from uuid import UUID

from sqlmodel import Session

from app.services.clock_report_service import build_daily_summary as build_daily_summary

__all__ = ["build_daily_summary"]
