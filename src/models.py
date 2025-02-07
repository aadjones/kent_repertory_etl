from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    section = Column(String)
    pages_covered = Column(String)
    # One chapter has many pages.
    pages = relationship("Page", back_populates="chapter")


class Page(Base):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"))
    page = Column(String, nullable=False)
    chapter = relationship("Chapter", back_populates="pages")
    # One page has many rubrics.
    rubrics = relationship("Rubric", back_populates="page")


class Rubric(Base):
    __tablename__ = "rubrics"
    id = Column(Integer, primary_key=True)
    page_id = Column(Integer, ForeignKey("pages.id"))
    parent_id = Column(Integer, ForeignKey("rubrics.id"), nullable=True)
    rubric = Column(String, nullable=False)
    # Store related rubrics as a comma-separated string (or JSON if your DB supports it)
    related_rubrics = Column(Text)
    page = relationship("Page", back_populates="rubrics")
    # Self-referential relationship for subrubrics.
    subrubrics = relationship("Rubric", backref="parent", remote_side=[id])
    # One rubric has many remedies.
    remedies = relationship("Remedy", back_populates="rubric")


class Remedy(Base):
    __tablename__ = "remedies"
    id = Column(Integer, primary_key=True)
    rubric_id = Column(Integer, ForeignKey("rubrics.id"))
    name = Column(String, nullable=False)
    grade = Column(Integer, nullable=False)
    rubric = relationship("Rubric", back_populates="remedies")
