import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.face import Person, FaceDetection
from app.models.photo import Photo
from app.models.user import User
from app.schemas.face import PersonCreate, PersonResponse, FaceDetectionResponse
from app.services.face_service import FaceService
from app.utils.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/faces", tags=["faces"])

face_service = FaceService()


@router.get("/persons", response_model=list[PersonResponse])
def list_persons(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persons = db.query(Person).all()
    result = []
    for person in persons:
        face_count = db.query(FaceDetection).filter(FaceDetection.person_id == person.id).count()
        response = PersonResponse.model_validate(person)
        response.face_count = face_count
        result.append(response)
    return result


@router.post("/persons", response_model=PersonResponse, status_code=status.HTTP_201_CREATED)
def create_person(
    person_data: PersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = Person(name=person_data.name)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.put("/persons/{person_id}", response_model=PersonResponse)
def update_person(
    person_id: int,
    person_data: PersonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    person.name = person_data.name
    db.commit()
    db.refresh(person)
    return person


@router.delete("/persons/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(
    person_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    db.query(FaceDetection).filter(FaceDetection.person_id == person_id).update({"person_id": None})
    db.delete(person)
    db.commit()


@router.get("/photos/{photo_id}/faces", response_model=list[FaceDetectionResponse])
def get_photo_faces(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.deleted == False).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    faces = db.query(FaceDetection).filter(FaceDetection.photo_id == photo_id).all()
    return faces


@router.post("/merge")
def merge_persons(
    source_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if source_id == target_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge person with itself")

    source = db.query(Person).filter(Person.id == source_id).first()
    target = db.query(Person).filter(Person.id == target_id).first()

    if not source or not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both persons not found")

    success = face_service.merge_persons(source_id, target_id, db)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to merge persons")

    db.commit()
    return {"message": f"Successfully merged {source.name} into {target.name}"}
