from kb_agent.lead_slots import extract_lead_slots, merge_lead_slots


def test_extracts_email_phone_preference_and_modality() -> None:
    s = extract_lead_slots("mi correo es juan.prueba@test.cl y mi telefono +56 9 1234 5678, presencial el jueves en la tarde")
    assert s == {
        "email": "juan.prueba@test.cl",
        "telefono": "+56912345678",
        "preferencia_visita": "jueves en la tarde",
        "modalidad": "presencial",
    }


def test_day_block_hour_and_relative_days() -> None:
    assert extract_lead_slots("el miércoles a las 15:30 por videollamada")["preferencia_visita"] == "miércoles a las 15:30"
    assert extract_lead_slots("el miércoles a las 15:30 por videollamada")["modalidad"] == "videollamada"
    assert extract_lead_slots("mañana en la mañana")["preferencia_visita"] == "mañana en la mañana"
    assert extract_lead_slots("puede ser esta semana en la tarde")["preferencia_visita"] == "esta semana en la tarde"
    assert extract_lead_slots("el sabado 11 am")["preferencia_visita"] == "sábado en la mañana a las 11"


def test_ignores_noise_and_short_numbers() -> None:
    assert extract_lead_slots("hola, para mi") == {}
    assert extract_lead_slots("son 560 suites?") == {}
    assert "telefono" not in extract_lead_slots("a las 15:00 hrs")


def test_merge_keeps_previous_and_lets_new_values_override() -> None:
    prev = {"email": "a@b.cl", "modalidad": "presencial"}
    assert merge_lead_slots(prev, {"telefono": "+56911111111"}) == {"email": "a@b.cl", "modalidad": "presencial", "telefono": "+56911111111"}
    assert merge_lead_slots(prev, {"email": "c@d.cl"})["email"] == "c@d.cl"
    assert merge_lead_slots(None, {}) == {}
