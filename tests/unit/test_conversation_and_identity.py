"""Entidad Conversation (agrupa turnos, TTL de cierre) + identidad unificada
por telefono entre canales. Ambas features comparten la misma zona de esquema.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from kb_agent.models_sql.conversation import Conversation, ConversationStatus
from kb_agent.models_sql.identity import Users
from kb_agent.models_sql.session import ChatHistory
from kb_agent.models_sql.turns import TurnKind, Turns
from tests.support.fakes import FakeTraitMapper, offline_orchestrator


# ── entidad conversacion ───────────────────────────────────────────────────


def test_turns_and_history_are_linked_to_a_conversation(negocio_kb: Path, tmp_db_url: str) -> None:
    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper())
    try:
        turn = o.handle_turn(external_id="wa:+56911112222", message="hola")
        assert turn["conversation_id"] is not None
        with o.SessionLocal() as s:
            convs = s.scalars(select(Conversation)).all()
            assert len(convs) == 1
            assert convs[0].status == ConversationStatus.OPEN
            # turno y mensajes ligados a la conversacion
            trow = s.scalars(select(Turns)).all()
            assert all(t.conversation_id == convs[0].id for t in trow)
            assert all(t.kind == TurnKind.AGENT for t in trow)
            hist = s.scalars(select(ChatHistory)).all()
            assert hist and all(h.conversation_id == convs[0].id for h in hist)
    finally:
        o.close()


def test_same_conversation_reused_within_ttl(negocio_kb: Path, tmp_db_url: str) -> None:
    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper())
    try:
        a = o.handle_turn(external_id="wa:+56911113333", message="hola")
        b = o.handle_turn(external_id="wa:+56911113333", message="que pizzas hay?")
        assert a["conversation_id"] == b["conversation_id"]
        with o.SessionLocal() as s:
            assert len(s.scalars(select(Conversation)).all()) == 1
    finally:
        o.close()


def test_expired_conversation_is_closed_and_a_new_one_opens(negocio_kb: Path, tmp_db_url: str) -> None:
    # TTL de 1 segundo: forzamos expiracion moviendo last_activity_at al pasado.
    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper())
    o.tuning.conversation_idle_ttl_s = 1
    try:
        first = o.handle_turn(external_id="wa:+56911114444", message="hola")
        with o.SessionLocal() as s:
            conv = s.get(Conversation, first["conversation_id"])
            conv.last_activity_at = datetime.now(timezone.utc) - timedelta(seconds=10)
            s.commit()

        second = o.handle_turn(external_id="wa:+56911114444", message="volvi")
        assert second["conversation_id"] != first["conversation_id"]
        with o.SessionLocal() as s:
            old = s.get(Conversation, first["conversation_id"])
            new = s.get(Conversation, second["conversation_id"])
            assert old.status == ConversationStatus.CLOSED and old.closed_at is not None
            assert new.status == ConversationStatus.OPEN
    finally:
        o.close()


def test_prompt_history_does_not_cross_conversation_boundary(negocio_kb: Path, tmp_db_url: str) -> None:
    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper())
    o.tuning.conversation_idle_ttl_s = 1
    try:
        o.handle_turn(external_id="wa:+56911115555", message="mensaje de la conversacion vieja")
        with o.SessionLocal() as s:
            conv = s.scalars(select(Conversation)).first()
            conv.last_activity_at = datetime.now(timezone.utc) - timedelta(seconds=10)
            s.commit()

        # nueva conversacion: el conversador NO debe recibir el historial viejo
        o.handle_turn(external_id="wa:+56911115555", message="hola de nuevo")
        last_call = o.conversador.calls[-1]
        hist_text = " ".join(m.get("content", "") for m in last_call.get("history", []))
        assert "conversacion vieja" not in hist_text
    finally:
        o.close()


# ── identidad unificada por telefono ───────────────────────────────────────


def test_phone_identity_unifies_user_across_channels(negocio_kb: Path, tmp_db_url: str) -> None:
    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper(), identity_key="phone")
    try:
        wa = o.handle_turn(external_id="whatsapp:+56 9 1234 5678", message="hola por whatsapp")
        web = o.handle_turn(external_id="web:+56912345678", message="hola por web")
        # mismo telefono -> mismo Users, aunque el external_id difiera por canal
        assert wa["user_id"] == web["user_id"]
        with o.SessionLocal() as s:
            users = s.scalars(select(Users)).all()
            assert len(users) == 1
            assert users[0].phone == "+56912345678"
    finally:
        o.close()


def test_external_id_identity_keeps_channels_separate(negocio_kb: Path, tmp_db_url: str) -> None:
    # default identity_key='external_id': cada canal es un usuario distinto
    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper())
    try:
        wa = o.handle_turn(external_id="whatsapp:+56912345678", message="hola")
        web = o.handle_turn(external_id="web:+56912345678", message="hola")
        assert wa["user_id"] != web["user_id"]
        with o.SessionLocal() as s:
            assert len(s.scalars(select(Users)).all()) == 2
    finally:
        o.close()


def test_phone_identity_ignores_channels_without_phone(negocio_kb: Path, tmp_db_url: str) -> None:
    o = offline_orchestrator(negocio_kb, tmp_db_url, trait_mapper=FakeTraitMapper(), identity_key="phone")
    try:
        a = o.handle_turn(external_id="ui:sessionA", message="hola")
        b = o.handle_turn(external_id="ui:sessionB", message="hola")
        # sin telefono no se unifica: dos usuarios distintos
        assert a["user_id"] != b["user_id"]
        with o.SessionLocal() as s:
            assert all(u.phone is None for u in s.scalars(select(Users)).all())
    finally:
        o.close()
