from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agnost_analytics.db.base import Base
from agnost_analytics.db.models import Conversation


def test_conversation_session_id_is_unique() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Conversation(
                session_id="sess_1",
                user_id="user_1",
                source="agnost_sdk",
                raw_payload={"session_id": "sess_1"},
            )
        )
        session.commit()

        session.add(
            Conversation(
                session_id="sess_1",
                user_id="user_2",
                source="agnost_sdk",
                raw_payload={"session_id": "sess_1"},
            )
        )

        try:
            session.commit()
            raise AssertionError("expected integrity error")
        except IntegrityError:
            session.rollback()
