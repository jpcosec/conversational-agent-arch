from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kb_agent.models_sql.identity import Base, UserTraits, Users


def _build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_users_and_traits_support_multiple_traits_and_shared_trait_ids() -> None:
    with _build_session() as session:
        user_a = Users(external_id="wa:+56911111111", channel="whatsapp")
        user_b = Users(external_id="wa:+56922222222", channel="whatsapp")
        session.add_all([user_a, user_b])
        session.flush()

        session.add_all(
            [
                UserTraits(
                    user_id=user_a.id,
                    trait_id="trait-vegetariano",
                    confidence=0.95,
                    source="extractor",
                ),
                UserTraits(
                    user_id=user_a.id,
                    trait_id="trait-prefiere-picante",
                    confidence=0.80,
                    source="extractor",
                ),
                UserTraits(
                    user_id=user_b.id,
                    trait_id="trait-vegetariano",
                    confidence=0.70,
                    source="extractor",
                ),
            ]
        )
        session.commit()

        persisted_user_a = session.scalar(
            select(Users).where(Users.external_id == "wa:+56911111111")
        )
        assert persisted_user_a is not None
        assert {trait.trait_id for trait in persisted_user_a.traits} == {
            "trait-vegetariano",
            "trait-prefiere-picante",
        }

        vegetarian_rows = session.scalars(
            select(UserTraits).where(UserTraits.trait_id == "trait-vegetariano")
        ).all()
        assert {row.user_id for row in vegetarian_rows} == {user_a.id, user_b.id}


def test_trait_id_accepts_arbitrary_strings_without_sldb_validation() -> None:
    arbitrary_trait_id = "trait:any/string::from-external-source?value=42"

    with _build_session() as session:
        user = Users(external_id="telegram:999", channel="telegram")
        session.add(user)
        session.flush()

        session.add(
            UserTraits(
                user_id=user.id,
                trait_id=arbitrary_trait_id,
                confidence=0.55,
                source="manual-test",
            )
        )
        session.commit()

        persisted = session.scalar(
            select(UserTraits).where(UserTraits.trait_id == arbitrary_trait_id)
        )
        assert persisted is not None
        assert persisted.trait_id == arbitrary_trait_id
