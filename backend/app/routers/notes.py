from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Note, User
from ..schemas import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


def _get_owned_note(note_id: int, user: User, db: Session) -> Note:
    note = db.get(Note, note_id)
    if note is None or note.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="笔记不存在")
    return note


@router.get("", response_model=list[NoteOut])
def list_notes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(Note)
        .filter(Note.owner_id == current_user.id)
        .order_by(Note.updated_at.desc())
        .all()
    )


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = Note(title=payload.title, content=payload.content, owner_id=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/{note_id}", response_model=NoteOut)
def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_note(note_id, current_user, db)


@router.put("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    payload: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_owned_note(note_id, current_user, db)
    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_owned_note(note_id, current_user, db)
    db.delete(note)
    db.commit()
