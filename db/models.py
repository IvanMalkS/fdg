from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, CheckConstraint, Float, Boolean, ForeignKey, DateTime, \
    UniqueConstraint, false
from sqlalchemy.orm import relationship, Mapped, mapped_column

from config import Config
from db.base import Base
from db.enums import UserRole
from sqlalchemy import BigInteger

class User(Base):
    __tablename__ = 'dama_users'
    
    id = Column(BigInteger, primary_key=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    username = Column(String(255), nullable=False)
    role = Column(String(255), nullable=False, default=UserRole.USER)
    test_results = relationship("TestResults", back_populates="user")

    __table_args__ = (
        CheckConstraint("first_name != '' OR last_name != ''", name='has_name'),
        {'extend_existing': True}
    )


class TestResults(Base):
    __tablename__ = 'dama_test_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey('dama_users.id'), nullable=False)
    dama_role = Column(String(255), nullable=False)
    dama_competence = Column(String(255), nullable=False)
    total_score = Column(Float, nullable=False)
    is_expert = Column(Boolean, nullable=False)
    test_date = Column(DateTime, default=datetime.utcnow)
    report_path: Mapped[str] = mapped_column(String, nullable=True) # Add this line

    user = relationship("User", back_populates="test_results")
    answers = relationship("TestAnswer", back_populates="test_result")
    analytics = relationship("Analytics", back_populates="test_result", uselist=False, cascade="all, delete-orphan")

class DAMACompetency(Base):
    __tablename__ = 'dama_competencies'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dama_role_name = Column(String(255), nullable=False)
    dama_competence_name = Column(String(255), nullable=False)

    __table_args__ = (
        CheckConstraint("dama_role_name != '' AND dama_competence_name != ''", name='non_empty_fields'),
        {'extend_existing': True}
    )


class DAMAQuestion(Base):
    __tablename__ = 'dama_questions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dama_role_name = Column(String(255), nullable=False)
    dama_competence_name = Column(String(255), nullable=False)
    question_type = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    question_answer = Column(Text, nullable=False)
    dama_knowledge_area = Column(Text)
    dama_main_job = Column(Text)

    __table_args__ = (
        CheckConstraint("question_type IN ('Теория', 'Практика')", name='valid_question_type'),
        {'extend_existing': True}
    )


class TestAnswer(Base):
    __tablename__ = 'dama_test_answers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    test_result_id = Column(Integer, ForeignKey('dama_test_results.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('dama_questions.id'), nullable=True)
    case_id = Column(Integer, ForeignKey('dama_cases.id'), nullable=True)
    answer_text = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    feedback = Column(Text, nullable=True)

    test_result = relationship("TestResults", back_populates="answers")
    question = relationship("DAMAQuestion")
    case = relationship("DAMACase")

class DAMACase(Base):
    __tablename__ = 'dama_cases'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dama_role_name = Column(String(255), nullable=False)
    dama_competence_name = Column(String(255), nullable=False)
    dama_main_job = Column(Text, nullable=False)
    situation = Column(Text, nullable=False)
    case_task = Column(Text, nullable=False)
    case_answer = Column(Text, nullable=False)
    dama_knowledge_area = Column(Text)

class DMARoles(Base):
    __tablename__ = 'dama_roles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    dama_role_name = Column(String(255), nullable=False)

class AiCreators(Base):
    __tablename__ = 'ai_creators'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    token = Column(String(255), nullable=False)
    url = Column(String(255), nullable=False)

    models = relationship("Models", back_populates="ai_creator", cascade="all, delete-orphan")

class Models(Base):
    __tablename__ = 'ai_models'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    selected = Column(Boolean, nullable=False, default=False)

    ai_creator_id = Column(Integer, ForeignKey('ai_creators.id'), nullable=False)
    ai_creator = relationship("AiCreators", back_populates="models")

class AiSettings(Base):
    __tablename__ = 'ai_settings'
    id = Column(Integer, primary_key=True, index=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)
    prompt = Column(Text, nullable=True, default=Config.DEFAULT_PROMPT)

    __table_args__ = (
        UniqueConstraint('id', name='single_row'),
        CheckConstraint("temperature >= 0 AND temperature <= 2", name="check_temperature_range"),
    )

class Analytics(Base):
    __tablename__ = 'ai_analytics'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_tokens = Column(Integer, nullable=False)
    test_result_id = Column(Integer, ForeignKey('dama_test_results.id'), nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)
    model = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    test_result = relationship("TestResults", back_populates="analytics")